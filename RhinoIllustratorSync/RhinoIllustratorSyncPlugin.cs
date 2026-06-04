using System;
using System.IO;
using System.Drawing;
using Rhino.PlugIns;
using Rhino.UI;

namespace RhinoIllustratorSync
{
    public class RhinoIllustratorSyncPlugin : PlugIn
    {
        public RhinoIllustratorSyncPlugin()
        {
            Instance = this;
        }

        public static RhinoIllustratorSyncPlugin? Instance { get; private set; }

        // You can override other PlugIn methods if needed

        protected override LoadReturnCode OnLoad(ref string errorMessage)
        {
            // Register the Eto dockable panel
            Type panelType = typeof(SyncPanel);
            System.Drawing.Icon? panelIcon = GetPanelIcon();

            Panels.RegisterPanel(this, panelType, "Illustrator Sync", panelIcon);

            return LoadReturnCode.Success;
        }

        private System.Drawing.Icon? GetPanelIcon()
        {
            try
            {
                var assembly = typeof(RhinoIllustratorSyncPlugin).Assembly;
                // Assembly resource name matches: AssemblyDefaultNamespace.FolderPath.Filename
                using (Stream? stream = assembly.GetManifestResourceStream("RhinoIllustratorSync.Resources.sync_icon.png"))
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
