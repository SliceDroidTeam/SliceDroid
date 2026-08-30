"""Tests for the unified webapp/src/analysis package."""

import json
from pathlib import Path

import pytest

from src.analysis.parser import parse_ftrace_log
from src.analysis.slicer import categorize_event, find_process, remove_apis, slice_events
from src.analysis.devices import build_device_summary, detect_sensitive_events, load_category_map
from src.analysis.network import (
    NetworkAccumulator,
    convert_port_endianness,
    int_to_ip,
    is_private_ip,
)
from src.analysis.windows import run_windowed_analysis
from src.analysis.pipeline import _dedupe_by_raw, run_analysis

FIXTURES = Path(__file__).parent / 'fixtures'
TRACE_FILE = FIXTURES / 'synthetic.trace'
CAT2DEVS_FILE = FIXTURES / 'cat2devs.json'

TARGET_APP = 'com.test.app'
TARGET_PID = 1000

# Raw trace IP integers (byte-swapped: __be32 read as u32 on little-endian)
PRIVATE_SRC_RAW = 117549248  # 192.168.1.7 (the device's own LOCAL WiFi address)
PUBLIC_DST_RAW = 584628317   # 93.184.216.34 (remote peer)
PRIVATE_DST_RAW = 83886090   # 10.0.0.5 (private remote peer)
PUBLIC_RAW_8844 = 67373064   # 8.8.4.4 (helper tests only)

CONTRACT_KEYS = {'meta', 'summary', 'timeline', 'network', 'sensitive', 'insights'}


def network_summary(raw_events, **window_kwargs):
    """Mirror the pipeline: window, dedupe by 'raw', accumulate once."""
    pruned = remove_apis(raw_events)
    windowed = run_windowed_analysis(pruned, TARGET_PID, **window_kwargs)
    accumulator = NetworkAccumulator()
    accumulator.update(_dedupe_by_raw(windowed['all_relevant_events']))
    return accumulator.summary()


@pytest.fixture()
def raw_events():
    return parse_ftrace_log(TRACE_FILE)


@pytest.fixture()
def sliced_events(raw_events):
    pruned = remove_apis(raw_events)
    return slice_events(pruned, TARGET_PID, asynchronous=True)


@pytest.fixture()
def analysis_result(tmp_path):
    return run_analysis(
        TRACE_FILE,
        target_app=TARGET_APP,
        cat2devs_path=CAT2DEVS_FILE,
        output_path=tmp_path / 'analysis.json',
        events_output_path=tmp_path / 'sliced_events.json',
    )


class TestParser:
    def test_event_count(self, raw_events):
        # 20 event lines in the fixture; the two header lines are skipped
        assert len(raw_events) == 20

    def test_k_dev_normalized(self, raw_events):
        probe_events = [e for e in raw_events
                        if e['event'] in ('read_probe', 'write_probe', 'ioctl_probe')]
        assert probe_events
        for e in probe_events:
            assert 'k_dev' in e['details']
            assert 'k__dev' not in e['details']

    def test_fields_typed(self, raw_events):
        e = raw_events[0]
        assert e['process'] == 'com.test.app'
        assert e['tid'] == 1001
        assert e['tgid'] == 1000
        assert isinstance(e['timestamp'], float)
        # hex detail values are decoded to int
        tcp = next(e for e in raw_events if e['event'] == 'tcp_sendmsg')
        assert tcp['details']['size'] == 1400

    def test_find_process(self, raw_events):
        assert find_process(raw_events, TARGET_APP) == TARGET_PID
        assert find_process(raw_events, 'does.not.exist.app') == 0


class TestSlicer:
    def test_binder_hop_contacts_read_in_slice(self, sliced_events):
        contacts_reads = [
            e for e in sliced_events
            if e['event'] == 'read_probe'
            and 'contacts2.db' in e['details'].get('pathname', '')
        ]
        assert len(contacts_reads) == 1
        # attributed via binder taint from the target to system_server
        assert contacts_reads[0]['tgid'] == 500

    def test_unix_stream_hop_write_in_slice(self, sliced_events):
        helper_writes = [
            e for e in sliced_events
            if e['event'] == 'write_probe'
            and e['details'].get('pathname') == '/data/misc/helper/helper.log'
        ]
        assert len(helper_writes) == 1
        assert helper_writes[0]['tgid'] == 2000

    def test_noise_not_in_slice(self, sliced_events):
        assert all(e['tgid'] != 3000 for e in sliced_events)
        assert all('noise' not in e['details'].get('pathname', '') for e in sliced_events)

    def test_api_markers_and_binder_plumbing_filtered(self, sliced_events):
        for e in sliced_events:
            assert 'binder' not in e['event']
            if e['event'] == 'write_probe':
                assert e['details'].get('pathname') != 'null'

    def test_private_udp_excluded_from_slice(self, sliced_events):
        assert all(e['event'] not in ('udp_sendmsg', 'udp_sendmsg_ret') for e in sliced_events)

    def test_exact_slice_composition(self, sliced_events):
        assert [e['event'] for e in sliced_events] == [
            'write_probe',      # target write to somefile.txt
            'read_probe',       # contacts read via binder taint
            'tcp_sendmsg',      # target TCP send to public peer (private LOCAL src kept)
            'tcp_sendmsg_ret',  # kretprobe with actual bytes
            'tcp_recvmsg',      # target TCP recv from the same public peer
            'tcp_recvmsg_ret',  # kretprobe with actual bytes
            'write_probe',      # helper write via unix_stream taint
        ]

    def test_categorize_event(self):
        assert categorize_event({'event': 'read_probe'}) == 'file_read'
        assert categorize_event({'event': 'write_probe'}) == 'file_write'
        assert categorize_event({'event': 'ioctl_probe'}) == 'ioctl'
        assert categorize_event({'event': 'binder_transaction'}) == 'binder'
        assert categorize_event({'event': 'tcp_sendmsg_ret'}) == 'network_tcp'
        assert categorize_event({'event': 'inet_sock_set_state'}) == 'network_tcp'
        assert categorize_event({'event': 'udp_recvmsg'}) == 'network_udp'
        assert categorize_event({'event': 'unix_stream_sendmsg'}) == 'unix_socket'
        assert categorize_event({'event': 'sock_queue_tail'}) == 'unix_socket'
        assert categorize_event({'event': 'hci_sock_sendmsg'}) == 'bluetooth'
        assert categorize_event({'event': 'sched_process_fork'}) == 'other'


class TestSensitiveDetection:
    def test_contacts_category_detected(self, sliced_events):
        cat2devs = load_category_map(CAT2DEVS_FILE)
        detected = detect_sensitive_events(sliced_events, cat2devs)
        assert len(detected['contacts']) == 1
        assert detected['sms'] == []
        assert detected['calendar'] == []
        assert detected['call_logs'] == []

    def test_device_summary_sensitive_section(self, sliced_events):
        cat2devs = load_category_map(CAT2DEVS_FILE)
        summary = build_device_summary(sliced_events, cat2devs)
        contacts = summary['sensitive']['contacts']
        assert contacts['detected'] is True
        assert contacts['event_count'] == 1
        assert contacts['devices'] == ['266338357 - 5057']
        assert summary['categories'] == {'contacts': 1}
        # non-sensitive devices are still counted
        assert '999 - 42' in summary['device_counts']
        assert '888 - 77' in summary['device_counts']


class TestNetwork:
    def test_convert_port_endianness(self):
        assert convert_port_endianness(47873) == 443
        assert convert_port_endianness(443) == 47873
        assert convert_port_endianness(13568) == 53

    def test_int_to_ip_little_endian_decode(self):
        # kernel __be32 read as u32 on little-endian: LSB is the first octet
        assert int_to_ip(PUBLIC_RAW_8844) == '8.8.4.4'
        assert int_to_ip(PUBLIC_DST_RAW) == '93.184.216.34'
        assert int_to_ip(PRIVATE_DST_RAW) == '10.0.0.5'
        assert int_to_ip(PRIVATE_SRC_RAW) == '192.168.1.7'
        assert int_to_ip(0) == '0.0.0.0'

    def test_is_private_ip_on_decoded_address(self):
        assert is_private_ip(PRIVATE_DST_RAW)       # 10.0.0.5
        assert is_private_ip(PRIVATE_SRC_RAW)       # 192.168.1.7
        assert not is_private_ip(PUBLIC_DST_RAW)    # 93.184.216.34
        assert not is_private_ip(PUBLIC_RAW_8844)   # 8.8.4.4
        assert is_private_ip(0)

    def test_network_metrics(self, raw_events):
        metrics = network_summary(raw_events)['metrics']

        assert set(metrics.keys()) == {
            'tcp_connections', 'udp_connections', 'unique_tcp_peers', 'unique_udp_peers',
            'tcp_bytes_sent', 'tcp_bytes_received', 'udp_bytes_sent', 'udp_bytes_received',
        }
        # the TCP flow has a private LOCAL src (192.168.1.7, the device's own
        # WiFi address) but a public remote peer, so it MUST be counted
        assert is_private_ip(PRIVATE_SRC_RAW)
        assert metrics['tcp_bytes_sent'] == 1400
        assert metrics['tcp_bytes_received'] == 800
        assert metrics['unique_tcp_peers'] == 1
        assert metrics['tcp_connections'] == 1
        # the UDP flow targeted a private 10.x REMOTE address and must be excluded
        assert metrics['udp_bytes_sent'] == 0
        assert metrics['unique_udp_peers'] == 0
        assert metrics['udp_connections'] == 0

    def test_peers_shape(self, raw_events):
        network = network_summary(raw_events)

        assert len(network['peers']) == 1
        peer = network['peers'][0]
        # recv-direction bytes are attributed to the REMOTE peer (dst_ip),
        # not to the local src_ip endpoint
        assert peer == {
            'ip': '93.184.216.34',
            'protocol': 'tcp',
            'ports': [443],
            'connections': 2,
            'bytes_sent': 1400,
            'bytes_received': 800,
        }

    def test_connections_shape(self, raw_events):
        network = network_summary(raw_events)

        # send and recv on the same socket collapse to ONE connection entry
        assert len(network['connections']) == 1
        conn = network['connections'][0]
        assert conn == {
            'protocol': 'tcp',
            'src': '192.168.1.7',
            'sport': 43210,
            'dst': '93.184.216.34',
            'dport': 443,
            'bytes_sent': 1400,
            'bytes_received': 800,
            'first_ts': 100.001,
            'last_ts': 100.00112,
        }

    def test_no_double_count_with_overlapping_windows(self, raw_events):
        # window_size=10/overlap=5 makes the windows revisit the tcp events;
        # deduplication before accumulation must keep the byte counts exact
        pruned = remove_apis(raw_events)
        windowed = run_windowed_analysis(pruned, TARGET_PID, window_size=10, overlap=5)
        assert windowed['window_count'] > 1

        raw_indices = [e['raw'] for e in windowed['all_relevant_events']]
        assert len(raw_indices) > len(set(raw_indices))  # overlaps really occurred

        accumulator = NetworkAccumulator()
        accumulator.update(_dedupe_by_raw(windowed['all_relevant_events']))
        metrics = accumulator.summary()['metrics']
        assert metrics['tcp_bytes_sent'] == 1400
        assert metrics['tcp_bytes_received'] == 800
        assert metrics['tcp_connections'] == 1
        assert metrics['unique_tcp_peers'] == 1


class TestPipeline:
    def test_contract_top_level_keys(self, analysis_result):
        assert set(analysis_result.keys()) == CONTRACT_KEYS

    def test_meta_section(self, analysis_result):
        meta = analysis_result['meta']
        assert set(meta.keys()) == {
            'trace_file', 'target', 'generated_at', 'window_size', 'overlap',
            'duration_s', 'total_events', 'sliced_events', 'windows',
        }
        assert meta['target'] == {
            'mode': 'app',
            'package': TARGET_APP,
            'name': None,
            'pids': [TARGET_PID],
        }
        assert meta['total_events'] == 20
        assert meta['sliced_events'] == 7
        assert meta['windows'] == 1
        assert isinstance(meta['duration_s'], float)

    def test_summary_section(self, analysis_result):
        summary = analysis_result['summary']
        assert summary['event_categories'] == {
            'file_write': 2,
            'file_read': 1,
            'network_tcp': 4,
        }
        assert summary['device_categories'] == {'contacts': 1}
        assert summary['top_processes'][0] == {
            'process': 'com.test.app', 'tgid': 1000, 'events': 5,
        }
        assert len(summary['top_processes']) == 3

    def test_timeline_section(self, analysis_result):
        timeline = analysis_result['timeline']
        assert timeline['categories'] == ['contacts']
        assert timeline['series'] == [
            {'category': 'contacts', 'points': [[0, 1]]},
        ]
        assert timeline['sensitive'] == [{
            'window': 0,
            'category': 'contacts',
            'identifier': '266338357 - 5057',
            'pathname': '/data/data/com.android.providers.contacts/databases/contacts2.db',
        }]
        assert timeline['network'] == [{'window': 0, 'tcp': 4, 'udp': 0}]

    def test_network_section(self, analysis_result):
        network = analysis_result['network']
        assert set(network.keys()) == {'metrics', 'peers', 'connections'}
        assert network['metrics']['tcp_bytes_sent'] == 1400
        assert network['metrics']['tcp_bytes_received'] == 800
        assert network['peers'][0]['ip'] == '93.184.216.34'
        assert network['peers'][0]['bytes_sent'] == 1400
        assert network['peers'][0]['bytes_received'] == 800

    def test_sensitive_section(self, analysis_result):
        sensitive = analysis_result['sensitive']
        assert len(sensitive) == 1
        entry = sensitive[0]
        assert set(entry.keys()) == {
            'category', 'window', 'process', 'tgid', 'identifier', 'pathname', 'timestamp',
        }
        assert entry['category'] == 'contacts'
        assert entry['window'] == 0
        assert entry['process'] == 'system_server'
        assert entry['tgid'] == 500
        assert entry['identifier'] == '266338357 - 5057'

    def test_insights_section(self, analysis_result):
        insights = analysis_result['insights']
        assert 3 <= len(insights) <= 6
        for insight in insights:
            assert set(insight.keys()) == {'level', 'text'}
            assert insight['level'] in ('info', 'warning')
            assert isinstance(insight['text'], str)
            assert '<' not in insight['text'] and '>' not in insight['text']  # no HTML
        # the contacts access is reported as a warning
        assert any(i['level'] == 'warning' and 'contacts' in i['text'] for i in insights)

    def test_json_serializable_and_persisted(self, tmp_path):
        output_file = tmp_path / 'analysis.json'
        events_file = tmp_path / 'sliced_events.json'
        result = run_analysis(
            TRACE_FILE,
            target_app=TARGET_APP,
            cat2devs_path=CAT2DEVS_FILE,
            output_path=output_file,
            events_output_path=events_file,
        )
        json.dumps(result)

        assert output_file.exists()
        with open(output_file) as f:
            on_disk = json.load(f)
        assert set(on_disk.keys()) == CONTRACT_KEYS

        assert events_file.exists()
        with open(events_file) as f:
            events_on_disk = json.load(f)
        assert len(events_on_disk) == 7

    def test_target_app_dict_form(self, tmp_path):
        result = run_analysis(
            TRACE_FILE,
            target_app={'package': TARGET_APP, 'name': 'Test App',
                        'process_names': ['com.test.app']},
            cat2devs_path=CAT2DEVS_FILE,
            output_path=tmp_path / 'analysis.json',
            events_output_path=tmp_path / 'sliced_events.json',
        )
        assert result['meta']['target'] == {
            'mode': 'app',
            'package': TARGET_APP,
            'name': 'Test App',
            'pids': [TARGET_PID],
        }

    def test_target_pid_mode(self, tmp_path):
        result = run_analysis(
            TRACE_FILE,
            target_pid=TARGET_PID,
            cat2devs_path=CAT2DEVS_FILE,
            output_path=tmp_path / 'analysis.json',
            events_output_path=tmp_path / 'sliced_events.json',
        )
        assert result['meta']['target']['mode'] == 'pid'
        assert result['meta']['target']['pids'] == [TARGET_PID]
        assert result['meta']['sliced_events'] == 7

    def test_run_analysis_requires_target(self, tmp_path):
        with pytest.raises(ValueError):
            run_analysis(TRACE_FILE, output_path=tmp_path / 'analysis.json')

    def test_run_analysis_unknown_process(self, tmp_path):
        with pytest.raises(ValueError, match='not found'):
            run_analysis(
                TRACE_FILE,
                target_app='does.not.exist',
                output_path=tmp_path / 'analysis.json',
            )

    def test_run_analysis_unknown_pid(self, tmp_path):
        # app.py maps ValueError messages containing 'not found' to 404
        with pytest.raises(ValueError, match='PID 4242 not found'):
            run_analysis(
                TRACE_FILE,
                target_pid=4242,
                output_path=tmp_path / 'analysis.json',
            )

    def test_run_analysis_unparseable_trace(self, tmp_path):
        bogus = tmp_path / 'bogus.trace'
        bogus.write_text('this is not an ftrace log\nnope\n')
        with pytest.raises(ValueError, match='No events could be parsed'):
            run_analysis(
                bogus,
                target_app=TARGET_APP,
                output_path=tmp_path / 'analysis.json',
            )
