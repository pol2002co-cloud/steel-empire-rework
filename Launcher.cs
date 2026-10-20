using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;
class Launcher {
 [STAThread] static void Main() {
  string dir=AppDomain.CurrentDomain.BaseDirectory;
  try {
   var p=new ProcessStartInfo(Path.Combine(dir,"SteelEmpire.exe"));
   p.WorkingDirectory=dir;p.UseShellExecute=false;
   p.EnvironmentVariables["__COMPAT_LAYER"]="HIGHDPIAWARE";
   using(var game=Process.Start(p)) {
    game.WaitForExit();
    File.AppendAllText(Path.Combine(dir,"rework-launch.log"),DateTime.Now.ToString("s")+" exit="+game.ExitCode+Environment.NewLine);
    if(game.ExitCode!=0)MessageBox.Show("게임이 오류 코드 "+game.ExitCode+"로 종료되었습니다.\nrework-launch.log를 확인해 주세요.","강철제국 리워크");
   }
  } catch(Exception e){MessageBox.Show(e.Message,"강철제국 리워크 실행 오류");}
 }
}
