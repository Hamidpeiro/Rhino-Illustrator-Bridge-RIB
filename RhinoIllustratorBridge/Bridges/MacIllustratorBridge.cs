using System;
using System.Diagnostics;
using System.IO;

namespace RhinoIllustratorBridge.Bridges
{
    public class MacIllustratorBridge : IIllustratorBridge
    {
        public string ExecuteJavaScript(string jsCode, out string error)
        {
            error = string.Empty;
            try
            {
                // Escape backslashes and double quotes for the AppleScript string literal.
                // In AppleScript:
                // \ becomes \\
                // " becomes \"
                string escapedJs = jsCode.Replace("\\", "\\\\").Replace("\"", "\\\"");

                string appleScript = $"with timeout of 600 seconds\n    tell application \"Adobe Illustrator\"\n        do javascript \"{escapedJs}\"\n    end tell\nend timeout";

                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = "osascript",
                    UseShellExecute = false,
                    RedirectStandardInput = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };

                using (Process? process = Process.Start(psi))
                {
                    if (process == null)
                    {
                        error = "Failed to start osascript process.";
                        return string.Empty;
                    }

                    using (StreamWriter sw = process.StandardInput)
                    {
                        sw.Write(appleScript);
                    }

                    string output = process.StandardOutput.ReadToEnd();
                    string stderr = process.StandardError.ReadToEnd();
                    process.WaitForExit();

                    if (process.ExitCode != 0)
                    {
                        error = $"AppleScript execution failed: {stderr.Trim()}";
                        return string.Empty;
                    }

                    return output.Trim();
                }
            }
            catch (Exception ex)
            {
                error = "macOS AppleScript Bridge failed: " + ex.Message;
                return string.Empty;
            }
        }
    }
}
