using System;
using System.IO;
using System.Drawing;
using System.Linq;
using System.Collections.Generic;
using System.Windows.Forms;
namespace SteelEditor {
 public sealed class Editor : Form {
  SaveModel model; Person person; bool loading;
  TextBox search=new TextBox(); ListView list=new ListView();
  Label title=new Label(), info=new Label(), footer=new Label();
  ComboBox state=new ComboBox(); Dictionary<int,NumericUpDown> inputs=new Dictionary<int,NumericUpDown>();
  CheckedListBox leadership=new CheckedListBox(),specials=new CheckedListBox();
  public Editor(string path){
   Text="강철제국 인물 에디터";Size=new Size(1120,810);MinimumSize=new Size(1050,760);StartPosition=FormStartPosition.CenterScreen;
   Font=new Font("맑은 고딕",10);BackColor=Color.FromArgb(244,247,251);
   var head=new Label{Text="강철제국  /  인물 에디터",Dock=DockStyle.Top,Height=64,BackColor=Color.FromArgb(25,40,64),ForeColor=Color.White,Font=new Font(Font.FontFamily,20,FontStyle.Bold),Padding=new Padding(20,12,0,0)};Controls.Add(head);
   var bar=new FlowLayoutPanel{Dock=DockStyle.Top,Height=56,Padding=new Padding(12,8,0,0)};
   AddButton(bar,"저장 파일 열기",delegate{Open();});AddButton(bar,"백업 후 저장",delegate{Save(false);});AddButton(bar,"다른 이름으로 저장",delegate{Save(true);});AddButton(bar,"백업 복원",delegate{Restore();});
   Controls.Add(bar);bar.BringToFront();
   footer.Dock=DockStyle.Bottom;footer.Height=56;footer.Padding=new Padding(16,8,8,0);Controls.Add(footer);
   var split=new SplitContainer{Size=new Size(1080,600),Dock=DockStyle.Fill,SplitterDistance=500,FixedPanel=FixedPanel.Panel1};Controls.Add(split);split.BringToFront();
   search.Dock=DockStyle.Top;search.Height=32;search.TextChanged+=delegate{if(!loading)RefreshList();};split.Panel1.Controls.Add(search);
   list.Dock=DockStyle.Fill;list.View=View.Details;list.FullRowSelect=true;list.MultiSelect=false;list.HideSelection=false;
   list.Columns.Add("이름",100);list.Columns.Add("병과",105);list.Columns.Add("레벨",50);list.Columns.Add("현재 상태",195);
   split.Panel1.Controls.Add(list);list.BringToFront();list.SelectedIndexChanged+=delegate{if(!loading&&list.SelectedItems.Count>0){if(!ApplyCurrent()){RefreshList();return;}SelectPerson((Person)list.SelectedItems[0].Tag);}};
   var right=new Panel{Dock=DockStyle.Fill,Padding=new Padding(18),AutoScroll=true};split.Panel2.Controls.Add(right);
   title.SetBounds(18,12,520,38);title.Font=new Font(Font.FontFamily,16,FontStyle.Bold);right.Controls.Add(title);
   int y=60;
   foreach(Stat s in SaveModel.Stats){var lab=new Label{Text=s.Name,Left=20,Top=y+4,Width=235,Height=28};var n=new NumericUpDown{Left=270,Top=y,Width=215,Minimum=s.Min,Maximum=s.Max,ThousandsSeparator=true};inputs.Add(s.Offset,n);right.Controls.Add(lab);right.Controls.Add(n);y+=39;}
   foreach(var pair in new[]{new {Box=leadership,Title="지휘능력",Names=SaveModel.Leadership},new {Box=specials,Title="특수능력",Names=SaveModel.Specials}}){
    right.Controls.Add(new Label{Text=pair.Title,Left=20,Top=y+4,Width=130});
    pair.Box.SetBounds(155,y,330,pair.Names.Length==5?75:100);pair.Box.CheckOnClick=true;pair.Box.MultiColumn=true;pair.Box.ColumnWidth=105;pair.Box.Items.AddRange(pair.Names);right.Controls.Add(pair.Box);y+=pair.Box.Height+12;
   }
   var sl=new Label{Text="상태 변경",Left=20,Top=y+4,Width=220};right.Controls.Add(sl);
   state.SetBounds(270,y,215,30);state.DropDownStyle=ComboBoxStyle.DropDownList;state.Items.AddRange(new object[]{"현재 상태 유지","생존","사망 / 복귀 대기"});state.SelectedIndex=0;right.Controls.Add(state);y+=42;
   info.SetBounds(20,y,475,66);right.Controls.Add(info);y+=70;
   var actions=new FlowLayoutPanel{Left=15,Top=y,Width=490,Height=46};right.Controls.Add(actions);
   AddButton(actions,"HP 최대 회복",delegate{if(person!=null){inputs[0x54].Value=inputs[0x58].Value;if(model.CanState(person))state.SelectedIndex=1;}});
   AddButton(actions,"변경 적용",delegate{if(ApplyCurrent()){RefreshList();UpdateFooter();}});
   AddButton(actions,"인물 변경 취소",delegate{if(person!=null){model.Reset(person);SelectPerson(person);RefreshList();UpdateFooter();}});
   FormClosing+=delegate(object sender,FormClosingEventArgs e){if(!CanLeave())e.Cancel=true;};
   if(path!=null)LoadFile(path);else{title.Text="저장 파일을 열어 주세요";info.Text="게임을 종료하고 Steel0.Sav 등의 저장 파일을 여세요. 이름으로 검색할 수 있습니다.";}
  }
  void AddButton(Control parent,string text,Action action){var b=new Button{Text=text,AutoSize=true,Height=34,Margin=new Padding(4),Padding=new Padding(7,2,7,2)};b.Click+=delegate{try{action();}catch(Exception ex){MessageBox.Show(this,ex.Message,"작업을 완료하지 못했습니다",MessageBoxButtons.OK,MessageBoxIcon.Warning);}};parent.Controls.Add(b);}
  bool ApplyCurrent(){if(person==null||loading)return true;try{var values=new Dictionary<int,int>();foreach(var pair in inputs)if((int)pair.Value.Value!=model.Get(person,pair.Key))values.Add(pair.Key,(int)pair.Value.Value);ReadAbilities(values,leadership,0x7c);ReadAbilities(values,specials,0x80);int st=state.SelectedIndex-1;if(values.Count>0||st!=-1)model.Apply(person,values,st);SelectPerson(person);UpdateFooter();return true;}catch(Exception e){MessageBox.Show(this,e.Message,"입력 확인");return false;}}
  void ReadAbilities(Dictionary<int,int> values,CheckedListBox box,int offset){int mask=(1<<box.Items.Count)-1;int value=model.Get(person,offset)&~mask;for(int i=0;i<box.Items.Count;i++)if(box.GetItemChecked(i))value|=1<<i;if(value!=model.Get(person,offset))values.Add(offset,value);}
  void SelectPerson(Person p){loading=true;person=p;title.Text=p.Name+" · "+(p.Outside?"포룸 밖 인물":p.Companion?"동료":"대기 용병");foreach(Stat s in SaveModel.Stats){int v=model.Get(p,s.Offset);inputs[s.Offset].Minimum=Math.Min(s.Min,v);inputs[s.Offset].Maximum=Math.Max(s.Max,v);inputs[s.Offset].Value=v;}for(int i=0;i<leadership.Items.Count;i++)leadership.SetItemChecked(i,(model.Get(p,0x7c)&(1<<i))!=0);for(int i=0;i<specials.Items.Count;i++)specials.SetItemChecked(i,(model.Get(p,0x80)&(1<<i))!=0);state.SelectedIndex=0;state.Enabled=model.CanState(p);info.Text=model.StateRestriction(p);loading=false;}
  void RefreshList(){loading=true;list.BeginUpdate();list.Items.Clear();if(model!=null)foreach(var p in model.People.Where(x=>x.Name.IndexOf(search.Text,StringComparison.CurrentCultureIgnoreCase)>=0)){var row=new ListViewItem(new string[]{p.Name,model.ClassName(p),model.Get(p,0x48).ToString(),(p.Outside?"[포룸 밖] ":"")+model.State(p)});row.Tag=p;list.Items.Add(row);if(p==person)row.Selected=true;}list.EndUpdate();loading=false;}
  void UpdateFooter(){footer.Text=model==null?"저장 파일을 선택하세요.":model.PathName+Environment.NewLine+"수정된 인물 "+model.ChangedCount+"명 · 변경 적용은 메모리에만 반영됩니다. ‘백업 후 저장’으로 파일에 기록하세요.";}
  bool CanLeave(){if(!ApplyCurrent())return false;return model==null||!model.Dirty||MessageBox.Show(this,"저장하지 않은 변경을 버릴까요?","저장되지 않은 변경",MessageBoxButtons.YesNo,MessageBoxIcon.Question)==DialogResult.Yes;}
  void LoadFile(string path){var next=new SaveModel(path);model=next;person=null;search.Text="";RefreshList();if(model.People.Count>0){SelectPerson(model.People[0]);RefreshList();}UpdateFooter();}
  void Open(){if(!CanLeave())return;using(var d=new OpenFileDialog{Title="강철제국 저장 파일 열기",Filter="강철제국 저장 (*.sav)|*.sav",InitialDirectory=AppDomain.CurrentDomain.BaseDirectory})if(d.ShowDialog(this)==DialogResult.OK)LoadFile(d.FileName);}
  void Save(bool copy){if(model==null||!ApplyCurrent())return;string dest=model.PathName;if(copy){using(var d=new SaveFileDialog{Title="새 저장 파일로 저장",Filter="강철제국 저장 (*.sav)|*.sav",InitialDirectory=Path.GetDirectoryName(dest),FileName="Steel3.Sav"}){if(d.ShowDialog(this)!=DialogResult.OK)return;dest=d.FileName;}}string backup=model.Save(dest,true);RefreshList();UpdateFooter();MessageBox.Show(this,"저장했습니다. 게임에서 해당 저장을 불러오세요.\n\n백업: "+backup,"저장 완료");}
  void Restore(){if(model==null)return;if(!CanLeave())return;using(var d=new OpenFileDialog{Title="복원할 에디터 백업 선택",Filter="에디터 백업 (*.bak)|*.bak",InitialDirectory=Path.Combine(Path.GetDirectoryName(model.PathName),"EditorBackups")}){if(d.ShowDialog(this)!=DialogResult.OK)return;if(MessageBox.Show(this,"현재 파일을 백업한 뒤 아래 파일을 복원합니다.\n"+model.PathName,"백업 복원",MessageBoxButtons.OKCancel)!=DialogResult.OK)return;model.Restore(d.FileName);LoadFile(model.PathName);}}
  [STAThread] static void Main(string[] args){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);try{if(args.Length==3&&args[0]=="--render-preview"){using(var f=new Editor(args[1])){f.Show();Application.DoEvents();using(var b=new Bitmap(f.Width,f.Height)){f.DrawToBitmap(b,new Rectangle(0,0,b.Width,b.Height));b.Save(args[2]);}f.Hide();}return;}Application.Run(new Editor(args.Length>0?args[0]:null));}catch(Exception e){if(args.Length==3&&args[0]=="--render-preview")File.WriteAllText(args[2]+".error.txt",e.ToString());else MessageBox.Show(e.Message,"강철제국 인물 에디터");}}
 }
}


