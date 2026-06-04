using System;
using System.Runtime.InteropServices;

namespace RhinoIllustratorSync.Bridges
{
    public static class IllustratorBridgeFactory
    {
        public static IIllustratorBridge Create()
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                return new WindowsIllustratorBridge();
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            {
                return new MacIllustratorBridge();
            }
            else
            {
                throw new PlatformNotSupportedException("Rhino-Illustrator sync is only supported on Windows and macOS.");
            }
        }
    }
}
