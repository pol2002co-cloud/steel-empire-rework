using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Windows.Forms;

class WideLauncher : Form {
 readonly string dir=AppDomain.CurrentDomain.BaseDirectory;
 ComboBox resolution=new ComboBox(); Button run=new Button();
 public WideLauncher(){
  Text="강철제국 16:9 런처";ClientSize=new Size(450,230);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;Font=new Font("맑은 고딕",10);
  Controls.Add(new Label{Text="강철제국 · 16:9 화면",Left=22,Top=20,Width=400,Height=32,Font=new Font(Font.FontFamily,17,FontStyle.Bold)});
  Controls.Add(new Label{Text="해상도",Left=24,Top=76,Width=90});
  resolution.SetBounds(120,70,300,32);resolution.DropDownStyle=ComboBoxStyle.DropDownList;resolution.Items.AddRange(new object[]{"1280 × 720","1600 × 900","1920 × 1080","2560 × 1440"});resolution.SelectedIndex=1;Controls.Add(resolution);
  Controls.Add(new Label{Text="원본 4:3 화면을 16:9로 가로 확대합니다.\n게임 시야는 그대로이며, 종료 시 기존 설정을 복원합니다.",Left=24,Top=112,Width=410,Height=50});
  run.Text="16:9 창 모드로 실행";run.SetBounds(120,174,300,36);Controls.Add(run);run.Click+=delegate{Launch();};AcceptButton=run;
 }
 public static string Configure(string input,int width,int height){
  var values=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase){{"width",width.ToString()},{"height",height.ToString()},{"windowed","true"},{"fullscreen","false"},{"maintas","false"},{"boxing","false"},{"adjmouse","true"},{"resizable","false"},{"savesettings","0"},{"posX","-32000"},{"posY","-32000"}};
  var output=new List<string>();bool section=false,found=false;
  foreach(string line in input.Replace("\r\n","\n").Split('\n')){
   string trim=line.Trim();
   if(trim.StartsWith("[")&&trim.EndsWith("]")){
    if(section){foreach(var v in values)output.Add(v.Key+"="+v.Value);values.Clear();}
    section=trim.Equals("[ddraw]",StringComparison.OrdinalIgnoreCase);found|=section;
   }
   int eq=trim.IndexOf('=');if(section&&eq>0&&values.ContainsKey(trim.Substring(0,eq).Trim()))continue;
   output.Add(line);
  }
  if(!found){output.Add("[ddraw]");section=true;}
  if(section)foreach(var v in values)output.Add(v.Key+"="+v.Value);
  return String.Join("\r\n",output);
 }
 void Launch(){
  bool locked=false;using(var mutex=new System.Threading.Mutex(false,"Local\\SteelEmpireWideLauncher")){
   try{
    try{locked=mutex.WaitOne(0);}catch(System.Threading.AbandonedMutexException){locked=true;}
    if(!locked)throw new IOException("16:9 런처가 이미 실행 중입니다.");
    if(Process.GetProcessesByName("SteelEmpire").Length>0)throw new IOException("실행 중인 강철제국을 종료한 뒤 다시 실행해 주세요.");
    string exe=Path.Combine(dir,"SteelEmpire.exe"),ini=Path.Combine(dir,"ddraw.ini");
    if(!File.Exists(exe)||!File.Exists(Path.Combine(dir,"ddraw.dll"))||!File.Exists(ini))throw new IOException("게임 폴더에서 실행해 주세요. SteelEmpire.exe, ddraw.dll, ddraw.ini가 필요합니다.");
    string backup=Path.Combine(dir,"WideLauncherBackups");Directory.CreateDirectory(backup);
    byte[] original=File.ReadAllBytes(ini);string saved=Path.Combine(backup,"ddraw-"+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff")+".ini");File.WriteAllBytes(saved,original);
    int[] widths={1280,1600,1920,2560};int width=widths[resolution.SelectedIndex],height=width*9/16;
    // Fit the client area within the monitor's working area while retaining 16:9.
    Rectangle work=Screen.FromControl(this).WorkingArea;
    int scale=Math.Min(width/16,Math.Min((work.Width-32)/16,(work.Height-80)/9));
    width=Math.Max(40,scale)*16;height=Math.Max(40,scale)*9;
    try{
     File.WriteAllText(ini,Configure(File.ReadAllText(ini,Encoding.Default),width,height),Encoding.Default);
     var start=new ProcessStartInfo(exe){WorkingDirectory=dir,UseShellExecute=false};start.EnvironmentVariables["__COMPAT_LAYER"]="HIGHDPIAWARE";
     Hide();using(var game=Process.Start(start)){game.WaitForExit();}
    }finally{File.WriteAllBytes(ini,original);Show();}
   }catch(Exception ex){Show();MessageBox.Show(this,ex.Message,"강철제국 16:9 런처",MessageBoxButtons.OK,MessageBoxIcon.Warning);}
   finally{if(locked)mutex.ReleaseMutex();}
  }
 }
 [STAThread]static void Main(string[] args){
  if(args.Length==1&&args[0]=="--self-test"){
   string input="[ddraw]\r\nwidth=1780\r\nheight=1335\r\nmaintas=true\r\nrenderer=auto\r\n[other]\r\nwidth=7\r\n";
   string result=Configure(input,1600,900);
   if(!result.Contains("width=1600")||!result.Contains("height=900")||!result.Contains("maintas=false")||!result.Contains("renderer=auto")||!result.Contains("[other]\r\nwidth=7")||result.Contains("width=1780"))throw new Exception("Configuration test failed");
   if(Configure(result,1600,900)!=result)throw new Exception("Configuration not idempotent");
   File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"wide-launcher-test.txt"),"PASS: resolution, aspect ratio, preserved unrelated settings, idempotent configuration");return;
  }
  Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new WideLauncher());
 }
}

