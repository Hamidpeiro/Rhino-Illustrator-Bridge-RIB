using System;
using System.IO;
using System.Text.Json;
using System.Collections.Generic;
using Eto.Forms;
using Eto.Drawing;
using Rhino;
using Rhino.UI;
using RhinoIllustratorBridge.Bridges;
using RhinoIllustratorBridge.Core;

namespace RhinoIllustratorBridge
{
    [System.Runtime.InteropServices.Guid("B4E78125-9CF7-49C3-ACBA-3E77BD0E81AA")]
    public class SyncPanel : Panel, IPanel
    {
        public static Guid PanelId => typeof(SyncPanel).GUID;

        private readonly string _desktopPath;
        private readonly string _aiArtboardsFile;
        private readonly string _rhinoCurvesFile;

        // UI Controls
        private Label _lblHeader = null!;
        private Label _lblImportStatus = null!;
        private Label _lblExportStatus = null!;
        private Button _btnImport = null!;
        private Button _btnExport = null!;
        private CheckBox _chkExportPics = null!;
        private Label _lblHatchTitle = null!;
        private CheckBox _chkHatchNone = null!;
        private RadioButtonList _rbHatchMode = null!;
        private Label _lblAnnotTitle = null!;
        private RadioButtonList _rbAnnotGroup = null!;
        private Label _lblStatus = null!;

        public SyncPanel()
        {
            _desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
            _aiArtboardsFile = Path.Combine(_desktopPath, "ai_artboards.json");
            _rhinoCurvesFile = Path.Combine(_desktopPath, "rhino_curves.json");

            InitializeUI();
        }

        // Rhino 8 IPanel constructor signature support
        public SyncPanel(uint documentRuntimeSerialNumber) : this()
        {
        }

        private void InitializeUI()
        {
            Padding = new Padding(12);

            _lblHeader = new Label
            {
                Text = "RHINO ⇄ ILLUSTRATOR BRIDGE",
                Font = new Font(FontFamilies.Sans, 11, FontStyle.Bold),
                TextAlignment = TextAlignment.Center
            };

            _lblImportStatus = new Label
            {
                Text = "📥 Last Imported: Never",
                Font = new Font(FontFamilies.Sans, 9),
                TextAlignment = TextAlignment.Left
            };

            _lblExportStatus = new Label
            {
                Text = "📤 Last Exported: Never",
                Font = new Font(FontFamilies.Sans, 9),
                TextAlignment = TextAlignment.Left
            };

            _btnImport = new Button
            {
                Text = "📥 Read Illustrator Artboards",
                Height = 28
            };
            _btnImport.Click += OnImportClick;

            _btnExport = new Button
            {
                Text = "📤 Send Curves to Illustrator",
                Height = 28
            };
            _btnExport.Click += OnExportClick;

            _chkExportPics = new CheckBox
            {
                Text = "Export Pictures",
                Checked = false,
                Height = 26
            };

            _lblHatchTitle = new Label
            {
                Text = "Hatch Export:",
                Font = new Font(FontFamilies.Sans, 9, FontStyle.Bold),
                TextAlignment = TextAlignment.Left
            };

            _chkHatchNone = new CheckBox
            {
                Text = "None",
                Checked = false
            };
            _chkHatchNone.CheckedChanged += OnHatchNoneChanged;

            _rbHatchMode = new RadioButtonList
            {
                Orientation = Orientation.Vertical
            };
            _rbHatchMode.DataStore = new[]
            {
                "Export hatches as solid fills",
                "Explode hatches (auto-detect solid)"
            };
            _rbHatchMode.SelectedIndex = 1;

            _lblAnnotTitle = new Label
            {
                Text = "Annotation Export:",
                Font = new Font(FontFamilies.Sans, 9, FontStyle.Bold),
                TextAlignment = TextAlignment.Left
            };

            _rbAnnotGroup = new RadioButtonList
            {
                Orientation = Orientation.Horizontal
            };
            _rbAnnotGroup.DataStore = new[] { "Group", "UnGroup" };
            _rbAnnotGroup.SelectedIndex = 1; // Default to UnGroup
            _rbAnnotGroup.ToolTip = "Export each annotation as a grouped set of lines and text.";

            _lblStatus = new Label
            {
                Text = "Status: Ready",
                Font = new Font(FontFamilies.Sans, 8.5f),
                Enabled = false,
                TextAlignment = TextAlignment.Left
            };

            // Layout assembly
            var layout = new DynamicLayout { Spacing = new Size(6, 6) };

            layout.AddRow(_lblHeader);
            layout.AddRow(CreateDivider());

            layout.AddRow(_lblImportStatus, null);
            layout.AddRow(_lblExportStatus, null);
            layout.AddRow(CreateDivider());

            layout.AddRow(_btnImport);
            layout.AddRow(_btnExport);
            layout.AddRow(_chkExportPics, null);
            layout.AddRow(CreateDivider());

            layout.AddRow(_lblHatchTitle, null);
            layout.AddRow(_chkHatchNone, null);
            layout.AddRow(_rbHatchMode, null);
            layout.AddRow(CreateDivider());

            layout.AddRow(_lblAnnotTitle, null);
            layout.AddRow(_rbAnnotGroup, null);
            layout.AddRow(CreateDivider());

            layout.AddRow(_lblStatus, null);

            Content = layout;
        }

        private Control CreateDivider()
        {
            var divider = new Panel
            {
                Height = 1,
                BackgroundColor = Colors.DarkGray
            };
            return divider;
        }

        private void OnHatchNoneChanged(object? sender, EventArgs e)
        {
            _rbHatchMode.Enabled = !(_chkHatchNone.Checked ?? false);
        }

        private void OnImportClick(object? sender, EventArgs e)
        {
            RhinoApp.InvokeOnUiThread((Action)(() => ImportArtboardsAction(false)));
        }

        private void OnExportClick(object? sender, EventArgs e)
        {
            RhinoApp.InvokeOnUiThread((Action)(() => ExportCurvesAction(false)));
        }

        private void ImportArtboardsAction(bool silent)
        {
            _lblStatus.Text = "Status: Connecting to Illustrator...";
            var bridge = IllustratorBridgeFactory.Create();
            string artboardsJson = string.Empty;
            string error = string.Empty;

            try
            {
                artboardsJson = bridge.ExecuteJavaScript(JsxTemplates.GetArtboardsJs, out error);
            }
            catch (Exception ex)
            {
                error = ex.Message;
            }

            List<ArtboardData>? artboards = null;

            if (string.IsNullOrEmpty(error) && !string.IsNullOrEmpty(artboardsJson))
            {
                if (artboardsJson.StartsWith("ERROR:"))
                {
                    error = artboardsJson.Substring(6);
                }
                else
                {
                    try
                    {
                        artboards = JsonSerializer.Deserialize<List<ArtboardData>>(artboardsJson);
                        if (artboards != null)
                        {
                            // Save backup to Desktop
                            File.WriteAllText(_aiArtboardsFile, artboardsJson);
                        }
                    }
                    catch (Exception ex)
                    {
                        error = "Failed to parse Illustrator response: " + ex.Message;
                    }
                }
            }

            if (artboards == null)
            {
                // Fallback to Desktop JSON
                bool fallback = false;
                if (File.Exists(_aiArtboardsFile))
                {
                    string msg = $"{error}\n\nWould you like to import the last exported artboards from Desktop JSON instead?";
                    var res = MessageBox.Show(msg, "Illustrator Connection Failed", MessageBoxButtons.YesNo, MessageBoxType.Question);
                    if (res == DialogResult.Yes)
                    {
                        fallback = true;
                    }
                }

                if (fallback)
                {
                    try
                    {
                        string localJson = File.ReadAllText(_aiArtboardsFile);
                        artboards = JsonSerializer.Deserialize<List<ArtboardData>>(localJson);
                        _lblStatus.Text = "Status: Imported from backup JSON";
                    }
                    catch (Exception ex)
                    {
                        if (!silent)
                        {
                            MessageBox.Show("❌ Error reading backup JSON:\n" + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxType.Error);
                        }
                        _lblStatus.Text = "Status: JSON read error";
                        return;
                    }
                }
                else
                {
                    if (!silent)
                    {
                        MessageBox.Show("❌ " + (string.IsNullOrEmpty(error) ? "Could not connect to Illustrator." : error), "Connection Error", MessageBoxButtons.OK, MessageBoxType.Error);
                    }
                    _lblStatus.Text = "Status: Connect failed";
                    return;
                }
            }

            if (artboards != null)
            {
                try
                {
                    ArtboardImporter.ImportArtboards(RhinoDoc.ActiveDoc, artboards);
                    _lblImportStatus.Text = "📥 Last Imported: " + DateTime.Now.ToString("HH:mm:ss");
                    _lblStatus.Text = "Status: Artboards imported!";
                    if (!silent)
                    {
                        MessageBox.Show($"✅ Imported {artboards.Count} artboards successfully!", "Success", MessageBoxButtons.OK, MessageBoxType.Information);
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show("❌ Error drawing artboards in Rhino:\n" + ex.Message, "Import Error", MessageBoxButtons.OK, MessageBoxType.Error);
                    _lblStatus.Text = "Status: Drawing error";
                }
            }
        }

        private void ExportCurvesAction(bool silent)
        {
            _lblStatus.Text = "Status: Exporting curves...";
            var doc = RhinoDoc.ActiveDoc;

            // Read preferences
            bool exportPics = _chkExportPics.Checked ?? false;
            string hatchMode = _chkHatchNone.Checked ?? false ? "none" : (_rbHatchMode.SelectedIndex == 0 ? "solid" : "explode");
            bool annotationGroup = _rbAnnotGroup.SelectedIndex == 0;

            List<ExportGroup> exportGroups;
            try
            {
                exportGroups = CurveExporter.BuildExportGroups(doc, exportPics, hatchMode, annotationGroup);
            }
            catch (Exception ex)
            {
                MessageBox.Show("❌ Error processing Rhino geometry:\n" + ex.Message, "Processing Error", MessageBoxButtons.OK, MessageBoxType.Error);
                _lblStatus.Text = "Status: Processing error";
                return;
            }

            if (exportGroups.Count == 0)
            {
                if (!silent)
                {
                    MessageBox.Show("❌ No Artboard sublayers found. Please click 'Read Illustrator Artboards' first to draw artboards.", "Error", MessageBoxButtons.OK, MessageBoxType.Error);
                }
                _lblStatus.Text = "Status: No artboards";
                return;
            }

            // Write JSON file to Desktop
            try
            {
                string jsonString = JsonSerializer.Serialize(exportGroups, new JsonSerializerOptions
                {
                    WriteIndented = true,
                    DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
                });
                File.WriteAllText(_rhinoCurvesFile, jsonString);
            }
            catch (Exception ex)
            {
                if (!silent)
                {
                    MessageBox.Show("❌ Error writing curves JSON:\n" + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxType.Error);
                }
                _lblStatus.Text = "Status: Export error";
                return;
            }

            _lblExportStatus.Text = "📤 Last Exported: " + DateTime.Now.ToString("HH:mm:ss");
            _btnExport.Text = "Update Curves to Illustrator";

            // Push to Illustrator
            _lblStatus.Text = "Status: Syncing with Illustrator...";
            var bridge = IllustratorBridgeFactory.Create();

            string curvesPathJs = _rhinoCurvesFile.Replace("\\", "/");
            string resultFile = Path.Combine(_desktopPath, "_rhino_sync_result.txt");
            string resultPathJs = resultFile.Replace("\\", "/");

            // Format JSX content
            string jsxContent = JsxTemplates.UpdateCurvesJs
                .Replace("__CURVES_PATH__", curvesPathJs)
                .Replace("__RESULT_PATH__", resultPathJs);

            string jsxPath = Path.Combine(_desktopPath, "_rhino_sync_update.jsx");

            try
            {
                File.WriteAllText(jsxPath, jsxContent);
            }
            catch (Exception ex)
            {
                _lblStatus.Text = "Status: Exported to JSON only";
                if (!silent)
                {
                    MessageBox.Show("❌ Failed to write temp JSX file:\n" + ex.Message, "Success (JSON only)", MessageBoxButtons.OK, MessageBoxType.Warning);
                }
                return;
            }

            // Remove old result file
            if (File.Exists(resultFile))
            {
                try { File.Delete(resultFile); } catch { }
            }

            // Run DoJavaScript via bridge
            string jsxPathJs = jsxPath.Replace("\\", "/");
            string execCode = $"var f = new File(\"{jsxPathJs}\"); $.evalFile(f);";

            string error = string.Empty;
            try
            {
                bridge.ExecuteJavaScript(execCode, out error);
            }
            catch (Exception ex)
            {
                error = ex.Message;
            }

            bool updatedDirectly = false;
            string totalUpdated = "0";

            if (string.IsNullOrEmpty(error))
            {
                // Wait for Illustrator to write the result file (up to 1.5 seconds)
                for (int i = 0; i < 15; i++)
                {
                    System.Threading.Thread.Sleep(100);
                    if (File.Exists(resultFile))
                    {
                        break;
                    }
                }

                if (File.Exists(resultFile))
                {
                    try
                    {
                        string resultText = File.ReadAllText(resultFile).Trim();
                        if (resultText.StartsWith("SUCCESS:"))
                        {
                            updatedDirectly = true;
                            totalUpdated = resultText.Substring(8);
                        }
                        else if (resultText.StartsWith("ERROR:"))
                        {
                            error = resultText.Substring(6);
                        }
                        else
                        {
                            error = "Unexpected result from Illustrator: " + resultText;
                        }
                    }
                    catch (Exception ex)
                    {
                        error = "Could not read result file: " + ex.Message;
                    }
                }
                else
                {
                    error = "Illustrator did not produce a result file. The script may have failed silently.";
                }
            }

            if (updatedDirectly)
            {
                _lblStatus.Text = "Status: Curves sent & synced!";
                if (!silent)
                {
                    MessageBox.Show($"✅ Sent and updated {totalUpdated} shapes in Illustrator successfully!", "Success", MessageBoxButtons.OK, MessageBoxType.Information);
                }
            }
            else
            {
                _lblStatus.Text = "Status: Exported to JSON only";
                if (!silent)
                {
                    string msg = $"✅ Curves exported to Desktop JSON.\n\n⚠️ Could not update Illustrator automatically:\n{error}";
                    MessageBox.Show(msg, "Export Successful", MessageBoxButtons.OK, MessageBoxType.Warning);
                }
            }
        }

        #region IPanel Methods
        public void PanelShown(uint documentRuntimeSerialNumber, ShowPanelReason reason)
        {
        }

        public void PanelHidden(uint documentRuntimeSerialNumber, ShowPanelReason reason)
        {
        }

        public void PanelClosing(uint documentRuntimeSerialNumber, bool orderIsClosing)
        {
        }
        #endregion
    }
}
