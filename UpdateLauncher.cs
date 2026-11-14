using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal sealed class ReleaseInfo {
 public Version Version; public string Tag, ZipUrl, HashUrl, ZipName; public long ZipSize;
}

internal static class UpdatePackage {
 public const string Repository="pol2002co-cloud/steel-empire-rework";
 public const string CurrentVersion="0.10.0";
 public const int MaxZipBytes=64*1024*1024;
 public static ReleaseInfo ParseRelease(string json) {
  var root=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(json);
  if(root.ContainsKey("draft")&&(bool)root["draft"] || root.ContainsKey("prerelease")&&(bool)root["prerelease"])throw new InvalidDataException("정식 릴리스가 아닙니다.");
  string tag=(string)root["tag_name"]; Version version;
  if(!tag.StartsWith("v",StringComparison.Ordinal)||!Version.TryParse(tag.Substring(1),out version))throw new InvalidDataException("릴리스 버전 형식이 잘못되었습니다.");
  var result=new ReleaseInfo{Version=version,Tag=tag,ZipName="SteelEmpire-Rework-"+tag+"-PatchOnly.zip"};
  foreach(object item in (System.Collections.IEnumerable)root["assets"]) {
   var asset=(Dictionary<string,object>)item; string name=(string)asset["name"];
   if(name!=result.ZipName&&name!="SHA256SUMS.txt")continue;
   string url=(string)asset["browser_download_url"];
   string expected="https://github.com/"+Repository+"/releases/download/"+tag+"/"+name;
   if(!String.Equals(url,expected,StringComparison.Ordinal))throw new InvalidDataException("배포 파일 주소가 저장소와 일치하지 않습니다.");
   if(name==result.ZipName){if(result.ZipUrl!=null)throw new InvalidDataException("중복된 패치 파일입니다.");result.ZipUrl=url;result.ZipSize=Convert.ToInt64(asset["size"]);}
   else {if(result.HashUrl!=null)throw new InvalidDataException("중복된 검증 파일입니다.");result.HashUrl=url;}
  }
  if(result.ZipUrl==null||result.HashUrl==null||result.ZipSize<1||result.ZipSize>MaxZipBytes)throw new InvalidDataException("패치 또는 SHA256SUMS.txt가 없거나 크기가 잘못되었습니다.");
  return result;
 }
 public static string ExpectedHash(string text,string name) {
  string found=null;
  foreach(string raw in text.TrimStart('\ufeff').Split('\n')) {
   string line=raw.Trim(); if(line.Length<67)continue;
   string file=line.Substring(64).Trim().TrimStart('*'); if(file!=name)continue;
   string hash=line.Substring(0,64).ToLowerInvariant();
   foreach(char c in hash)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))throw new InvalidDataException("체크섬 형식이 잘못되었습니다.");
   if(found!=null)throw new InvalidDataException("중복된 체크섬입니다.");found=hash;
  }
  if(found==null)throw new InvalidDataException("패치 체크섬이 없습니다.");return found;
 }
 public static string Hash(string path) {using(var stream=File.OpenRead(path))using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
 public static void Verify(string path,long bytes,string expected) {
  if(new FileInfo(path).Length!=bytes||!String.Equals(Hash(path),expected,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("다운로드 파일 검증 실패. 게임 파일은 변경하지 않았습니다.");
 }
 public static void Download(string url,string destination,int limit) {
  var request=(HttpWebRequest)WebRequest.Create(url);request.UserAgent="SteelEmpire-Rework-Updater/"+CurrentVersion;request.Timeout=30000;request.ReadWriteTimeout=30000;
  using(var response=(HttpWebResponse)request.GetResponse()) {
   if(response.ContentLength>limit)throw new InvalidDataException("다운로드 파일이 너무 큽니다.");
   using(var input=response.GetResponseStream())using(var output=new FileStream(destination,FileMode.CreateNew)) {
    byte[] buffer=new byte[16384];int n,total=0;
    while((n=input.Read(buffer,0,buffer.Length))>0){total=checked(total+n);if(total>limit)throw new InvalidDataException("다운로드 제한을 초과했습니다.");output.Write(buffer,0,n);}
   }
  }
 }
 public static void Extract(string zip,string destination,string version) {
  string prefix=Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
  var paths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);long total=0;
  using(var archive=ZipFile.OpenRead(zip)) {
   if(archive.Entries.Count>1000)throw new InvalidDataException("패치 파일 수가 너무 많습니다.");
   // Validate the whole archive before creating any file.
   foreach(var entry in archive.Entries) {
    string name=entry.FullName.Replace('/',Path.DirectorySeparatorChar);
    if(String.IsNullOrEmpty(name)||Path.IsPathRooted(name)||name.IndexOf(':')>=0||name.IndexOf('\0')>=0)throw new InvalidDataException("안전하지 않은 ZIP 경로입니다.");
    string path=Path.GetFullPath(Path.Combine(destination,name));
    if(!path.StartsWith(prefix,StringComparison.OrdinalIgnoreCase)||!paths.Add(path.TrimEnd(Path.DirectorySeparatorChar)))throw new InvalidDataException("ZIP 경로가 중복되거나 압축 폴더 밖을 가리킵니다.");
    if((((uint)entry.ExternalAttributes>>16)&0xf000)==0xa000)throw new InvalidDataException("링크 파일은 설치할 수 없습니다.");
    total=checked(total+entry.Length);if(total>128L*1024*1024)throw new InvalidDataException("압축 해제 크기가 너무 큽니다.");
   }
   if(Directory.Exists(destination))throw new IOException("압축 해제 폴더가 이미 존재합니다.");
   Directory.CreateDirectory(destination);
   foreach(var entry in archive.Entries) {
    string path=Path.GetFullPath(Path.Combine(destination,entry.FullName.Replace('/',Path.DirectorySeparatorChar)));
    if(entry.Name.Length==0){Directory.CreateDirectory(path);continue;}
    Directory.CreateDirectory(Path.GetDirectoryName(path));
    using(var input=entry.Open())using(var output=new FileStream(path,FileMode.CreateNew)) {
     byte[] buffer=new byte[16384];int n;long count=0;
     while((n=input.Read(buffer,0,buffer.Length))>0){count=checked(count+n);if(count>entry.Length)throw new InvalidDataException("ZIP 내부 파일 크기가 잘못되었습니다.");output.Write(buffer,0,n);}
     if(count!=entry.Length)throw new InvalidDataException("ZIP 내부 파일이 잘렸습니다.");
    }
   }
  }
  foreach(string name in new[]{"Install-Patch.ps1","PatchEngine.cs","patch-manifest.json","Restore-Patch.ps1"})if(!File.Exists(Path.Combine(destination,name)))throw new InvalidDataException("필수 설치 파일이 없습니다: "+name);
  var manifest=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(destination,"patch-manifest.json"),Encoding.UTF8));
  if((string)manifest["version"]!=version)throw new InvalidDataException("패치 내부 버전이 릴리스와 다릅니다.");
 }
 public static string Quote(string value) {if(value.IndexOf('"')>=0||value.IndexOf('\r')>=0||value.IndexOf('\n')>=0)throw new ArgumentException("잘못된 경로입니다.");return "\""+value+(value.EndsWith("\\",StringComparison.Ordinal)?"\\":"")+"\"";}
 [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool QueryFullProcessImageName(IntPtr process,uint flags,StringBuilder path,ref int size);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 public static bool GameBusy(string dir,int exceptPid) {
  foreach(string name in new[]{"SteelEmpire","SteelRework","SteelRework169","SteelReworkQHD","SteelCharacterEditor","SteelEquipmentEditor","SteelReworkLauncher"})
   foreach(var process in Process.GetProcessesByName(name))using(process) {
    if(process.Id==exceptPid)continue;
    IntPtr handle=OpenProcess(0x1000,false,process.Id);
    if(handle==IntPtr.Zero){if(!process.HasExited)return true;continue;}
    try {var path=new StringBuilder(32768);int length=path.Capacity;if(!QueryFullProcessImageName(handle,0,path,ref length))return true;if(String.Equals(Path.GetDirectoryName(path.ToString()),dir,StringComparison.OrdinalIgnoreCase))return true;}
    finally {CloseHandle(handle);}
   }
  return false;
 }
 public static int Apply(string[] args) {
  if(args.Length!=7)throw new ArgumentException("업데이트 인수가 잘못되었습니다.");
  string stage=Path.GetFullPath(args[1]),dir=Path.GetFullPath(args[2]).TrimEnd('\\');int parent=int.Parse(args[3]);
  string temp=Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\')+"\\";
  if(!stage.StartsWith(temp+"SteelReworkUpdate-",StringComparison.OrdinalIgnoreCase)||Path.GetDirectoryName(stage)+"\\"!=temp)throw new InvalidDataException("업데이트 임시 경로가 잘못되었습니다.");
  string zip=Path.Combine(stage,"patch.zip");Verify(zip,long.Parse(args[6]),args[4]);
  string unpack=Path.Combine(stage,"install");Extract(zip,unpack,args[5]);
  try {using(var p=Process.GetProcessById(parent)){if(!p.WaitForExit(30000))throw new IOException("런처가 종료되지 않았습니다.");}}catch(ArgumentException){}
  if(GameBusy(dir,Process.GetCurrentProcess().Id))throw new IOException("게임·런처·에디터를 종료한 후 다시 업데이트해 주세요.");
  string powershell=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),"WindowsPowerShell\\v1.0\\powershell.exe");
  var start=new ProcessStartInfo(powershell,"-NoProfile -STA -ExecutionPolicy Bypass -File "+Quote(Path.Combine(unpack,"Install-Patch.ps1"))+" -GamePath "+Quote(dir)){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=unpack};
  string output,error;int exit;
  using(var p=Process.Start(start)) {
   string capturedError=null;var readError=new Thread(delegate(){capturedError=p.StandardError.ReadToEnd();});readError.Start();output=p.StandardOutput.ReadToEnd();p.WaitForExit();readError.Join();error=capturedError;exit=p.ExitCode;
  }
  File.WriteAllText(Path.Combine(stage,"install.log"),output+Environment.NewLine+error,Encoding.UTF8);
  if(exit!=0)throw new IOException("업데이트 설치 실패. 로그: "+Path.Combine(stage,"install.log")+Environment.NewLine+error);
  Process.Start(new ProcessStartInfo(Path.Combine(dir,"SteelReworkLauncher.exe")){UseShellExecute=false,WorkingDirectory=dir});return 0;
 }
}

internal sealed class UpdateLauncher : Form {
 readonly string dir=AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
 readonly ComboBox resolution=new ComboBox();readonly Button run=new Button(),update=new Button();readonly Label status=new Label();bool checking;
 public UpdateLauncher() {
  Text="강철제국 리워크 v"+UpdatePackage.CurrentVersion;ClientSize=new Size(470,245);Font=new Font("맑은 고딕",10);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;
  Controls.Add(new Label{Text="강철제국 리워크",Left=22,Top=18,Width=420,Height=35,Font=new Font(Font.FontFamily,19,FontStyle.Bold)});
  Controls.Add(new Label{Text="실행 모드",Left=24,Top=76,Width=95});resolution.SetBounds(125,70,320,30);resolution.DropDownStyle=ComboBoxStyle.DropDownList;resolution.Items.AddRange(new object[]{"기본 화면","16:9 · 최대 1920 × 1080","16:9 · 최대 2560 × 1440"});resolution.SelectedIndex=2;Controls.Add(resolution);
  status.SetBounds(24,115,420,55);status.Text="시작할 때 GitHub 최신 패치를 자동 확인합니다.";Controls.Add(status);
  run.SetBounds(24,185,230,38);run.Text="게임 실행";Controls.Add(run);run.Click+=delegate{Launch();};
  update.SetBounds(267,185,178,38);update.Text="업데이트 확인";Controls.Add(update);update.Click+=delegate{Check();};Shown+=delegate{Check();};
 }
 void Launch() {try {string[] names={"SteelRework.exe","SteelRework169.exe","SteelReworkQHD.exe"};Process.Start(new ProcessStartInfo(Path.Combine(dir,names[resolution.SelectedIndex])){WorkingDirectory=dir,UseShellExecute=false});}catch(Exception ex){MessageBox.Show(this,ex.Message,"실행 오류");}}
 void Check() {
  if(checking)return;checking=true;update.Enabled=false;run.Enabled=false;status.Text="GitHub 최신 버전을 확인하고 있습니다…";
  var worker=new BackgroundWorker();string stage=null;ReleaseInfo release=null;string hash=null;
  worker.DoWork+=delegate {
   ServicePointManager.SecurityProtocol=(SecurityProtocolType)3072;
   stage=Path.Combine(Path.GetTempPath(),"SteelReworkUpdate-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(stage);
   string json=Path.Combine(stage,"release.json");UpdatePackage.Download("https://api.github.com/repos/"+UpdatePackage.Repository+"/releases/latest",json,2*1024*1024);release=UpdatePackage.ParseRelease(File.ReadAllText(json,Encoding.UTF8));
   if(release.Version<=new Version(UpdatePackage.CurrentVersion))return;
   if(UpdatePackage.GameBusy(dir,Process.GetCurrentProcess().Id))throw new IOException("새 버전 "+release.Tag+"이 있습니다. 게임·다른 런처·에디터를 종료한 뒤 업데이트 확인을 눌러 주세요.");
   string sums=Path.Combine(stage,"SHA256SUMS.txt"),zip=Path.Combine(stage,"patch.zip");
   UpdatePackage.Download(release.HashUrl,sums,1024*1024);hash=UpdatePackage.ExpectedHash(File.ReadAllText(sums,Encoding.UTF8),release.ZipName);
   UpdatePackage.Download(release.ZipUrl,zip,UpdatePackage.MaxZipBytes);UpdatePackage.Verify(zip,release.ZipSize,hash);
  };
  worker.RunWorkerCompleted+=delegate(object sender,RunWorkerCompletedEventArgs e) {
   checking=false;update.Enabled=true;run.Enabled=true;
   if(e.Error!=null){status.Text="업데이트 확인·설치 준비 실패. 게임 실행은 가능합니다.";MessageBox.Show(this,e.Error.Message,"업데이트 안내",MessageBoxButtons.OK,MessageBoxIcon.Information);return;}
   if(release.Version<=new Version(UpdatePackage.CurrentVersion)){status.Text="최신 버전입니다. v"+UpdatePackage.CurrentVersion;Directory.Delete(stage,true);return;}
   try {
    string workerPath=Path.Combine(stage,"SteelReworkUpdateWorker.exe");File.Copy(Application.ExecutablePath,workerPath);
    string args="--apply "+UpdatePackage.Quote(stage)+" "+UpdatePackage.Quote(dir)+" "+Process.GetCurrentProcess().Id+" "+hash+" "+release.Version+" "+release.ZipSize;
    Process.Start(new ProcessStartInfo(workerPath,args){UseShellExecute=false,WorkingDirectory=stage});Application.Exit();
   }catch(Exception ex){status.Text="자동 설치를 시작하지 못했습니다.";MessageBox.Show(this,ex.Message,"업데이트 오류");}
  };worker.RunWorkerAsync();
 }
 [STAThread] static int Main(string[] args) {
  try {if(args.Length>0&&args[0]=="--apply")return UpdatePackage.Apply(args);Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new UpdateLauncher());return 0;}
  catch(Exception ex){MessageBox.Show(ex.Message,"강철제국 업데이트 오류",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;}
 }
}
