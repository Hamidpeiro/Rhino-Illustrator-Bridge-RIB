using System;
using System.Reflection;
using System.Runtime.InteropServices;

namespace RhinoIllustratorSync.Bridges
{
    public class WindowsIllustratorBridge : IIllustratorBridge
    {
        public string ExecuteJavaScript(string jsCode, out string error)
        {
            error = string.Empty;
            object? ai = null;

            // Strategy 1: Activator.CreateInstance via GetTypeFromProgID
            // For Illustrator (which is a single-instance local COM server),
            // this usually binds to the active instance if it is already running.
            try
            {
                Type? tp = Type.GetTypeFromProgID("Illustrator.Application");
                if (tp != null)
                {
                    ai = Activator.CreateInstance(tp);
                }
            }
            catch
            {
                // Fall through
            }


            // Strategy 3: P/Invoke direct to OleAut32 if above failed
            if (ai == null && RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                try
                {
                    ai = GetActiveObjectWin32("Illustrator.Application");
                }
                catch
                {
                    // Fall through
                }
            }

            if (ai == null)
            {
                error = "Could not connect to Adobe Illustrator. Please ensure Illustrator is running and a document is open.";
                return string.Empty;
            }

            // Execute DoJavaScript via COM Reflection
            try
            {
                Type comType = ai.GetType();
                object[] args = new object[] { jsCode };
                object? result = comType.InvokeMember(
                    "DoJavaScript",
                    BindingFlags.InvokeMethod,
                    null,
                    ai,
                    args
                );
                return result?.ToString() ?? string.Empty;
            }
            catch (TargetInvocationException tie)
            {
                error = "Illustrator script error: " + (tie.InnerException?.Message ?? tie.Message);
                return string.Empty;
            }
            catch (Exception ex)
            {
                error = "COM Execution failed: " + ex.Message;
                return string.Empty;
            }
        }

        #region Win32 P/Invoke Fallback
        [DllImport("ole32.dll", PreserveSig = false)]
        private static extern void CLSIDFromProgID([MarshalAs(UnmanagedType.LPWStr)] string lpszProgID, out Guid pclsid);

        [DllImport("oleaut32.dll", PreserveSig = false)]
        private static extern void GetActiveObject(ref Guid rclsid, IntPtr pvReserved, [MarshalAs(UnmanagedType.IUnknown)] out object ppunk);

        private static object? GetActiveObjectWin32(string progId)
        {
            try
            {
                CLSIDFromProgID(progId, out Guid clsid);
                GetActiveObject(ref clsid, IntPtr.Zero, out object punk);
                return punk;
            }
            catch
            {
                return null;
            }
        }
        #endregion
    }
}
