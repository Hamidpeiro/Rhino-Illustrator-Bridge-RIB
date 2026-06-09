using System;
using System.IO;
using System.Drawing;
using Rhino;
using Rhino.PlugIns;
using Rhino.UI;

[assembly: System.Runtime.InteropServices.Guid("9051039a-6429-4e1a-8912-d1a1f4f83035")]
[assembly: PlugInDescription(DescriptionType.Email, "hamidpeiro@Yahoo.com")] // Update this email if you want
[assembly: PlugInDescription(DescriptionType.Organization, "Hamid Peiro")]
[assembly: PlugInDescription(DescriptionType.WebSite, "https://github.com/Hamidpeiro/Rhino-Illustrator-Bridge-RIB")]

namespace RhinoIllustratorBridge
{
    public class RhinoIllustratorBridgePlugin : PlugIn
    {
        public RhinoIllustratorBridgePlugin()
        {
            Instance = this;
        }

        public static RhinoIllustratorBridgePlugin? Instance { get; private set; }

        // You can override other PlugIn methods if needed

        protected override LoadReturnCode OnLoad(ref string errorMessage)
        {
            // Register the Eto dockable panel
            Type panelType = typeof(SyncPanel);
            System.Drawing.Icon? panelIcon = GetPanelIcon();

            Panels.RegisterPanel(this, panelType, "Illustrator Bridge", panelIcon);

            // Subscribe to Idle event to auto-show the toolbar once Rhino is ready
            RhinoApp.Idle += OnIdleShowToolbar;

            return LoadReturnCode.Success;
        }

        private void OnIdleShowToolbar(object? sender, EventArgs e)
        {
            RhinoApp.Idle -= OnIdleShowToolbar; // Unsubscribe so it only runs once at startup
            try
            {
                // Auto-show the toolbar group from our RUI library
                RhinoApp.RunScript("_-ShowToolbar \"RhinoIllustratorBridge\" \"RhinoIllustratorBridge\"", false);
            }
            catch
            {
                // Silently handle exceptions if Rhino initialization state blocks scripting
            }
        }

        private System.Drawing.Icon? GetPanelIcon()
        {
            try
            {
                var assembly = typeof(RhinoIllustratorBridgePlugin).Assembly;
                // Assembly resource name matches: AssemblyDefaultNamespace.FolderPath.Filename
                using (Stream? stream = assembly.GetManifestResourceStream("RhinoIllustratorBridge.Resources.sync_icon.png"))
                {
                    if (stream == null) return null;
                    using (var bitmap = new Bitmap(stream))
                    {
                        using (var resized = new Bitmap(bitmap, new Size(24, 24)))
                        {
                            IntPtr hIcon = resized.GetHicon();
                            return System.Drawing.Icon.FromHandle(hIcon);
                        }
                    }
                }
            }
            catch
            {
                // Fallback for macOS where System.Drawing.Icon and GetHicon are not fully supported or throw
                return null;
            }
        }
    }
}
