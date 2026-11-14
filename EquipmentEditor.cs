using System;using System.IO;using System.Linq;using System.Drawing;using System.Collections.Generic;using System.Windows.Forms;
namespace SteelEditor {
 public sealed class EquipmentEditor:Form {
  EquipmentModel model;EquipmentRow row;bool loading;TextBox search=new TextBox();ListView list=new ListView();Panel fields=new Panel();Label info=new Label();Dictionary<int,NumericUpDown> inputs=new Dictionary<int,NumericUpDown>();
  public EquipmentEditor(string directory){
   Text="강철제국 장비 에디터 v0.10.0";Size=new Size(1120,850);MinimumSize=new Size(1020,740);Font=new Font("맑은 고딕",10);StartPosition=FormStartPosition.CenterScreen;
   var toolbar=new FlowLayoutPanel{Dock=DockStyle.Top,Height=52};Controls.Add(toolbar);
   Button(toolbar,"게임 폴더 열기",OpenFolder);Button(toolbar,"저장 파일의 보유 장비",OpenSave);Button(toolbar,"백업 후 저장",Save);Button(toolbar,"업데이트 전 변경 재적용",Profile);
   info.Dock=DockStyle.Bottom;info.Height=80;info.Padding=new Padding(12);Controls.Add(info);
   var split=new SplitContainer{Size=new Size(1080,680),Dock=DockStyle.Fill,SplitterDistance=530,FixedPanel=FixedPanel.Panel1};Controls.Add(split);split.BringToFront();
   search.Dock=DockStyle.Top;search.TextChanged+=delegate{RefreshRows();};split.Panel1.Controls.Add(search);
   list.Dock=DockStyle.Fill;list.View=View.Details;list.FullRowSelect=true;list.MultiSelect=false;list.HideSelection=false;list.Columns.Add("이름",305);list.Columns.Add("구분",125);list.Columns.Add("ID",80);split.Panel1.Controls.Add(list);list.BringToFront();
   list.SelectedIndexChanged+=delegate{if(!loading&&list.SelectedItems.Count>0){if(Apply())Select((EquipmentRow)list.SelectedItems[0].Tag);}};
   fields.Dock=DockStyle.Fill;fields.AutoScroll=true;split.Panel2.Controls.Add(fields);FormClosing+=delegate(object s,FormClosingEventArgs e){if(!CanLeave())e.Cancel=true;};
   if(directory!=null)LoadGame(directory);
  }
  void Button(Control parent,string text,Action action){var b=new Button{Text=text,AutoSize=true,Height=38,Margin=new Padding(5)};b.Click+=delegate{try{action();}catch(Exception e){MessageBox.Show(this,e.Message,"장비 에디터",MessageBoxButtons.OK,MessageBoxIcon.Warning);}};parent.Controls.Add(b);}
  void LoadGame(string directory){model=new EquipmentModel(directory);row=null;RefreshRows();if(model.Rows.Count>0)Select(model.Rows[0]);UpdateInfo();}
  void UpdateInfo(){info.Text=model==null?"리워크가 설치된 게임 폴더를 선택하세요.":model.IsSave?"저장 장비 모드: 아군·적군의 현재 보유 장비 수치를 변경합니다. 게임 종료 후 저장하고 게임에서 다시 불러오세요.\n"+model.SavePath:"장비 기준 모드: 차량·항공기와 조합용 차체·포탑의 제작/생성 기준을 변경합니다. 이미 보유한 장비는 ‘저장 파일의 보유 장비’에서 수정하세요.\n수치 변경 프로필은 자동 보관됩니다. 게임 업데이트 후 ‘업데이트 전 변경 재적용’ → ‘백업 후 저장’을 누르세요.";}
  void RefreshRows(){loading=true;list.Items.Clear();if(model!=null)foreach(var r in model.Rows.Where(x=>x.Name.IndexOf(search.Text,StringComparison.CurrentCultureIgnoreCase)>=0)){var item=new ListViewItem(new[]{r.Name,r.Table=="machine.dat"?"차량·항공기":r.Table=="body.dat"?"조합 차체":r.Table=="turret.dat"?"조합 포탑":"저장 장비",r.Id.ToString()});item.Tag=r;list.Items.Add(item);}loading=false;}
  void Select(EquipmentRow selected){loading=true;row=selected;inputs.Clear();fields.Controls.Clear();fields.Controls.Add(new Label{Text=row.Name,Left=18,Top=14,Width=490,Height=44,Font=new Font(Font,FontStyle.Bold)});int y=66;
   foreach(var field in row.Fields){int value=model.Get(row,field.Offset);fields.Controls.Add(new Label{Text=field.Name,Left=18,Top=y+5,Width=235});var n=new NumericUpDown{Left=265,Top=y,Width=200,Minimum=Math.Min(field.Min,value),Maximum=Math.Max(field.Max,value),Value=value,ThousandsSeparator=true};inputs.Add(field.Offset,n);fields.Controls.Add(n);y+=38;}
   var actions=new FlowLayoutPanel{Left=12,Top=y+5,Width=480,Height=52};fields.Controls.Add(actions);Button(actions,"변경 적용",delegate{Apply();});Button(actions,"선택 장비 변경 취소",delegate{model.Reset(row);Select(row);});loading=false;
  }
  bool Apply(){if(row==null||loading)return true;try{var changes=inputs.Where(x=>(int)x.Value.Value!=model.Get(row,x.Key)).ToDictionary(x=>x.Key,x=>(int)x.Value.Value);model.Apply(row,changes);return true;}catch(Exception e){MessageBox.Show(this,e.Message,"입력 확인");return false;}}
  bool CanLeave(){return Apply()&&(model==null||!model.Dirty||MessageBox.Show(this,"저장하지 않은 장비 변경을 버릴까요?","장비 변경",MessageBoxButtons.YesNo)==DialogResult.Yes);}
  void OpenFolder(){if(!CanLeave())return;using(var d=new FolderBrowserDialog{Description="원본 보유자용 강철제국 리워크 설치 폴더",SelectedPath=AppDomain.CurrentDomain.BaseDirectory})if(d.ShowDialog(this)==DialogResult.OK)LoadGame(d.SelectedPath);}
  void OpenSave(){if(model==null)throw new InvalidOperationException("게임 폴더를 먼저 여세요.");if(!CanLeave())return;using(var d=new OpenFileDialog{Filter="강철제국 저장 (*.sav)|*.sav",InitialDirectory=model.DirectoryName})if(d.ShowDialog(this)==DialogResult.OK){var next=new EquipmentModel(model.DirectoryName);next.OpenSave(d.FileName);model=next;row=null;RefreshRows();Select(model.Rows[0]);UpdateInfo();}}
  void Profile(){if(model==null)throw new InvalidOperationException("게임 폴더를 먼저 여세요.");if(!Apply())return;model.ImportProfile();if(row!=null)Select(row);MessageBox.Show(this,"변경 프로필을 불러왔습니다. 백업 후 저장하면 게임에 적용됩니다.","변경 재적용");}
  void Save(){if(model==null||!Apply())return;string backup=model.Save();UpdateInfo();MessageBox.Show(this,"저장했습니다.\n백업: "+backup,"장비 저장 완료");}
  [STAThread]static void Main(string[] args){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);try{if(args.Length==3&&args[0]=="--render-preview"){using(var f=new EquipmentEditor(args[1])){f.Show();Application.DoEvents();using(var b=new Bitmap(f.Width,f.Height)){f.DrawToBitmap(b,new Rectangle(0,0,b.Width,b.Height));b.Save(args[2]);}f.Hide();}return;}Application.Run(new EquipmentEditor(args.Length>0?args[0]:AppDomain.CurrentDomain.BaseDirectory));}catch(Exception e){MessageBox.Show(e.Message,"강철제국 장비 에디터");}}
 }
}
