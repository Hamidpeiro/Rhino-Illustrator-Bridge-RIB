namespace RhinoIllustratorSync.Bridges
{
    public interface IIllustratorBridge
    {
        string ExecuteJavaScript(string jsCode, out string error);
    }
}
