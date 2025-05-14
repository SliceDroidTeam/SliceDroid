# **How to Run `simple_trace_sock.sh` via ADB**

This guide explains how to execute `simple_trace_sock.sh` on an Android device using ADB over USB. The process includes transferring the script, setting permissions, disabling SELinux (if needed), running the script, and retrieving the generated trace file.

---

## **1. Prerequisites**
- **ADB Installed**: Ensure you have ADB installed on your PC.  
- **USB Debugging Enabled**: Enable USB debugging from **Developer Options** on your Android device.  
- **Root Access**: Your device must be rooted to execute tracing commands.  

---

## **2. Transfer the Script to the Device**
First, connect your Android device via USB and push the script to a writable directory:

```bash
adb push simple_trace_sock.sh /data/local/tmp/
```

Verify the script is successfully transferred:

```bash
adb shell ls -l /data/local/tmp/simple_trace_sock.sh
```

---

## **3. Grant Execution Permissions**
Ensure the script has executable permissions:

```bash
adb shell chmod +x /data/local/tmp/simple_trace_sock.sh
```

Check permissions:

```bash
adb shell ls -l /data/local/tmp/simple_trace_sock.sh
```

---

## **4. Disable SELinux (If Required)**
If SELinux is enforcing and blocking execution, temporarily disable it:

```bash
adb shell su -c setenforce 0
```

Confirm SELinux is set to **permissive**:

```bash
adb shell getenforce
```

It should return:

```bash
Permissive
```

---

## **5. Execute the Script**
Start an interactive ADB shell:

```bash
adb shell
```

Gain root access:

```bash
su
```

Run the script using: 
```bash
su -c sh /data/local/tmp/simple_trace_sock.sh
```

### Stopping the Script
To stop the script, simply press Enter in the terminal.

---

## **6. Verify the Output**
Once the script completes, check if the trace file was created:

```bash
ls -l /data/local/tmp/trace.trace.gz
```

If the file exists, proceed to pull it from the device.

---

## **7. Retrieve the Trace File**
Exit the ADB shell:

```bash
exit
exit
```

Now, pull the generated trace file to your computer:

```bash
adb pull /data/local/tmp/trace.trace.gz .
```

Ensure the file is saved locally:

```bash
ls -l trace.trace.gz
```

---

## **8. Additional Notes & Troubleshooting**

### **Missing Directories (e.g., `/sys/kernel/tracing/` Errors)**
If your script fails due to missing paths, check:

```bash
ls /sys/kernel/tracing/events/kprobes/
```

Modify the script to match the available event names.

### **Script Format Issues**  
If you encounter errors related to unexpected characters (`^M` or `\r`), your script might have Windows-style line endings. Convert it to UNIX format before execution.

You can fix it directly on your Android device using `dos2unix`:

```bash
adb shell su -c 'dos2unix /data/local/tmp/simple_trace_sock.sh'
```

This ensures the script runs correctly by converting line endings to the proper UNIX format.

---
