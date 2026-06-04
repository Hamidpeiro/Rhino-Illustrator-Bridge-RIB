using Rhino;
using Rhino.Commands;
using Rhino.UI;

namespace RhinoIllustratorSync
{
    [System.Runtime.InteropServices.Guid("7623910A-B391-4F91-9876-1B90FE197A2E")]
    public class ShowSyncPanelCommand : Command
    {
        public ShowSyncPanelCommand()
        {
            Instance = this;
        }

        public static ShowSyncPanelCommand? Instance { get; private set; }

        public override string EnglishName => "ShowRhinoIllustratorSync";

        protected override Result RunCommand(RhinoDoc doc, RunMode mode)
        {
            var panelId = SyncPanel.PanelId;
            bool isOpen = Panels.IsPanelVisible(panelId);

            if (!isOpen)
            {
                Panels.OpenPanel(panelId);
                RhinoApp.WriteLine("Rhino <-> Illustrator Sync panel opened.");
            }
            else
            {
                Panels.ClosePanel(panelId);
                RhinoApp.WriteLine("Rhino <-> Illustrator Sync panel closed.");
            }

            return Result.Success;
        }
    }
}
