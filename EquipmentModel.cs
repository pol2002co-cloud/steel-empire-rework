using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;

namespace SteelEditor {
 public sealed class EquipmentRow {
  public string Table,Name; public int Id,Offset; public Stat[] Fields;
  public override string ToString(){return Name;}
 }
 public sealed class EquipmentModel {
  static readonly Encoding Korean=Encoding.GetEncoding(949,EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback);
  public static readonly Stat[] MachineFields={new Stat(0x28,"최대 HP",1,100000),new Stat(0x2c,"대인 공격",0,9999),new Stat(0x30,"대공 공격",0,9999),new Stat(0x34,"대갑 공격",0,9999),new Stat(0x38,"대벽 공격",0,9999),new Stat(0x3c,"방어",0,9999),new Stat(0x40,"발사속도",0,100),new Stat(0x44,"사정거리 (0없음 1단 2장 3전)",0,3),new Stat(0x48,"타격범위 (0없음 1단 2폭)",0,2),new Stat(0x4c,"명중 보정",-999,999),new Stat(0x50,"회피 보정",-999,999),new Stat(0x54,"기량 보정",-999,999),new Stat(0x58,"이동속도",1,100)};
  public static readonly Stat[] BodyFields={new Stat(0x40,"HP",1,100000),new Stat(0x44,"방어",0,9999),new Stat(0x4c,"회피 보정",-999,999),new Stat(0x70,"이동속도",1,100)};
  public static readonly Stat[] TurretFields={new Stat(0x44,"발사속도",0,100),new Stat(0x48,"사정거리 (0없음 1단 2장 3전)",0,3),new Stat(0x4c,"타격범위 (0없음 1단 2폭)",0,2),new Stat(0x50,"명중 보정",-999,999),new Stat(0x54,"기량 보정",-999,999),new Stat(0x58,"대인 공격",0,9999),new Stat(0x5c,"대공 공격",0,9999),new Stat(0x60,"대갑 공격",0,9999),new Stat(0x64,"대벽 공격",0,9999)};
  public static readonly Stat[] SavedFields={new Stat(0x54,"현재 HP",0,100000),new Stat(0x58,"최대 HP",1,100000),new Stat(0x5c,"대인 공격",0,9999),new Stat(0x60,"대공 공격",0,9999),new Stat(0x64,"대갑 공격",0,9999),new Stat(0x68,"대벽 공격",0,9999),new Stat(0x6c,"방어",0,9999),new Stat(0x70,"발사속도",0,100),new Stat(0x74,"사정거리 (0없음 1단 2장 3전)",0,3),new Stat(0x78,"타격범위 (0없음 1단 2폭)",0,2),new Stat(0x7c,"명중 보정",-999,999),new Stat(0x80,"회피 보정",-999,999),new Stat(0x84,"기량 보정",-999,999),new Stat(0x88,"이동속도",0,100)};
  public string DirectoryName,SavePath; public List<EquipmentRow> Rows=new List<EquipmentRow>();
  public Dictionary<string,byte[]> Tables=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase);
  Dictionary<string,byte[]> originalTables=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase),patch;
  byte[] originalPatch,originalSave; public byte[] SaveData;
  static int I(byte[] b,int o){if(o<0||o>b.Length-4)throw new InvalidDataException("잘린 장비 데이터입니다.");return BitConverter.ToInt32(b,o);}
  static void W(byte[] b,int o,int n){Buffer.BlockCopy(BitConverter.GetBytes(n),0,b,o,4);}
  static string Name(byte[] b,int o){int n=Array.IndexOf(b,(byte)0,o,32);if(n<0)throw new InvalidDataException("장비 이름 형식이 다릅니다.");return Korean.GetString(b,o,n-o);}
  public static Dictionary<string,byte[]> ReadPak(byte[] bytes){
   if(bytes.Length<9||bytes[bytes.Length-1]!=0x12)throw new InvalidDataException("지원하지 않는 PAK 형식입니다.");
   int start=I(bytes,bytes.Length-9),count=I(bytes,bytes.Length-5),q=start;
   if(start<0||start>bytes.Length-9||count<0||count>10000)throw new InvalidDataException("PAK 목록이 손상되었습니다.");
   var files=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase);
   for(int i=0;i<count;i++){
    if(q>bytes.Length-24)throw new InvalidDataException("PAK 목록이 잘렸습니다.");
    int len=bytes[q],flag=bytes[q+1],offset=I(bytes,q+2),size=I(bytes,q+6),raw=I(bytes,q+10);
    if(len<1||q+15+len>bytes.Length-9||offset<0||size<0||raw<0||raw>64*1024*1024||offset>start-size||flag>1)throw new InvalidDataException("PAK 항목이 손상되었습니다.");
    string name=Korean.GetString(bytes,q+14,len);q+=15+len;
    byte[] data=new byte[raw];
    if(flag==0){if(size!=raw)throw new InvalidDataException("PAK 크기가 다릅니다.");Buffer.BlockCopy(bytes,offset,data,0,raw);}
    else {int input=offset,end=offset+size,output=0;while(input<end){int bits=bytes[input++];for(int bit=0;bit<8&&input<end;bit++){
      if((bits&(1<<bit))!=0){if(input>end-2)throw new InvalidDataException("압축 데이터가 잘렸습니다.");int token=bytes[input]|bytes[input+1]<<8;input+=2;int distance=token&4095,n=(token>>12)+2;if(distance==0||distance>output||output>raw-n)throw new InvalidDataException("압축 참조가 잘못되었습니다.");for(int j=0;j<n;j++){data[output]=data[output-distance];output++;}}
      else {if(output>=raw)throw new InvalidDataException("압축 데이터 크기가 다릅니다.");data[output++]=bytes[input++];}
     }}if(output!=raw)throw new InvalidDataException("압축 데이터가 잘렸습니다.");}
    if(files.ContainsKey(name))throw new InvalidDataException("중복 PAK 항목입니다.");files.Add(name,data);
   }
   if(q!=bytes.Length-9)throw new InvalidDataException("PAK 목록 길이가 다릅니다.");return files;
  }
  public static byte[] WritePak(Dictionary<string,byte[]> files){
   using(var data=new MemoryStream())using(var index=new MemoryStream())using(var w=new BinaryWriter(index)){
    foreach(var entry in files){byte[] name=Korean.GetBytes(entry.Key);if(name.Length==0||name.Length>255)throw new InvalidDataException("잘못된 PAK 이름입니다.");w.Write((byte)name.Length);w.Write((byte)0);w.Write((int)data.Position);w.Write(entry.Value.Length);w.Write(entry.Value.Length);w.Write(name);w.Write((byte)0);data.Write(entry.Value,0,entry.Value.Length);}
    int at=(int)data.Position;byte[] table=index.ToArray();data.Write(table,0,table.Length);using(var tail=new BinaryWriter(data,Encoding.ASCII,true)){tail.Write(at);tail.Write(files.Count);tail.Write((byte)0x12);}return data.ToArray();
   }
  }
  public EquipmentModel(string directory){
   DirectoryName=Path.GetFullPath(directory);var names=new[]{"machine.dat","body.dat","turret.dat"};
   foreach(string file in new[]{"Data.pak","patch102.pak","patch103.pak","patch104.pak"}){
    string path=Path.Combine(DirectoryName,file);if(!File.Exists(path)){if(file=="Data.pak"||file=="patch104.pak")throw new FileNotFoundException("원본 보유자용 리워크가 설치된 폴더를 선택하세요.",path);continue;}
    byte[] bytes=File.ReadAllBytes(path);var current=ReadPak(bytes);foreach(string name in names)if(current.ContainsKey(name))Tables[name]=(byte[])current[name].Clone();
    if(file=="patch104.pak"){originalPatch=bytes;patch=current;}
   }
   int[] sizes={240,324,412},counts={24,33,55};Stat[][] fields={MachineFields,BodyFields,TurretFields};
   for(int t=0;t<3;t++){
    string name=names[t];if(!Tables.ContainsKey(name))throw new InvalidDataException("장비 기준 데이터가 없습니다: "+name);byte[] b=Tables[name];
    if(I(b,0)!=counts[t]||b.Length!=4+counts[t]*sizes[t])throw new InvalidDataException("지원하지 않는 장비 목록입니다: "+name);
    originalTables[name]=(byte[])b.Clone();for(int i=0;i<counts[t];i++){int o=4+i*sizes[t];Rows.Add(new EquipmentRow{Table=name,Name=Name(b,o),Id=i+1,Offset=o,Fields=fields[t]});}
   }
  }
  public bool IsSave{get{return SavePath!=null;}}
  public bool Dirty{get{return IsSave?!originalSave.SequenceEqual(SaveData):Tables.Any(x=>!x.Value.SequenceEqual(originalTables[x.Key]));}}
  public int Get(EquipmentRow row,int field){return I(IsSave?SaveData:Tables[row.Table],row.Offset+field);}
  public void Apply(EquipmentRow row,Dictionary<int,int> changes){
   if(!Rows.Contains(row))throw new InvalidOperationException("다른 장비 목록의 항목입니다.");
   foreach(var v in changes){var field=row.Fields.FirstOrDefault(x=>x.Offset==v.Key);if(field==null||v.Value<field.Min||v.Value>field.Max)throw new InvalidDataException("장비 수치가 허용 범위를 벗어났습니다.");}
   if(IsSave){int hp=changes.ContainsKey(0x54)?changes[0x54]:Get(row,0x54),max=changes.ContainsKey(0x58)?changes[0x58]:Get(row,0x58);if(hp>max)throw new InvalidDataException("현재 HP는 최대 HP보다 클 수 없습니다.");}
   byte[] b=IsSave?SaveData:Tables[row.Table];foreach(var v in changes)W(b,row.Offset+v.Key,v.Value);
  }
  public void Reset(EquipmentRow row){int size=IsSave?160:row.Table=="machine.dat"?240:row.Table=="body.dat"?324:412;Buffer.BlockCopy(IsSave?originalSave:originalTables[row.Table],row.Offset,IsSave?SaveData:Tables[row.Table],row.Offset,size);}
  public string ProfilePath{get{return Path.Combine(DirectoryName,"EquipmentEditorChanges.ini");}}
  public void ImportProfile(){
   if(IsSave)throw new InvalidOperationException("장비 기준 데이터 모드에서 적용하세요.");
   var pending=new List<KeyValuePair<EquipmentRow,Dictionary<int,int>>>();
   foreach(string line in File.ReadAllLines(ProfilePath,Encoding.UTF8)){
    if(String.IsNullOrWhiteSpace(line)||line.StartsWith("#"))continue;string[] tokens=line.Split('|');int id,offset,value;
    if(tokens.Length!=4||!Int32.TryParse(tokens[1],out id)||!Int32.TryParse(tokens[2],out offset)||!Int32.TryParse(tokens[3],out value))throw new InvalidDataException("장비 변경 프로필 형식이 다릅니다.");
    var row=Rows.SingleOrDefault(x=>x.Table==tokens[0]&&x.Id==id);var field=row==null?null:row.Fields.FirstOrDefault(x=>x.Offset==offset);
    if(field==null||value<field.Min||value>field.Max)throw new InvalidDataException("장비 변경 프로필 수치가 지원 범위를 벗어났습니다.");pending.Add(new KeyValuePair<EquipmentRow,Dictionary<int,int>>(row,new Dictionary<int,int>{{offset,value}}));
   }
   foreach(var change in pending)Apply(change.Key,change.Value);
  }
  void SaveProfile(){
   var values=new Dictionary<string,string>();if(File.Exists(ProfilePath))foreach(string line in File.ReadAllLines(ProfilePath,Encoding.UTF8)){string[] t=line.Split('|');if(t.Length==4)values[String.Join("|",t.Take(3).ToArray())]=t[3];}
   foreach(var row in Rows)foreach(var field in row.Fields)if(Get(row,field.Offset)!=I(originalTables[row.Table],row.Offset+field.Offset))values[row.Table+"|"+row.Id+"|"+field.Offset]=Get(row,field.Offset).ToString();
   string temp=ProfilePath+"."+Guid.NewGuid().ToString("N")+".tmp";try{File.WriteAllLines(temp,new[]{"# Steel Empire equipment numeric changes v1"}.Concat(values.OrderBy(x=>x.Key).Select(x=>x.Key+"|"+x.Value)),Encoding.UTF8);if(File.Exists(ProfilePath))File.Replace(temp,ProfilePath,null);else File.Move(temp,ProfilePath);}finally{if(File.Exists(temp))File.Delete(temp);}
  }
  public void OpenSave(string path){
   var verified=new SaveModel(path);byte[] b=verified.Original;var found=new List<EquipmentRow>();var machines=Rows.Where(x=>x.Table=="machine.dat").ToDictionary(x=>x.Id,x=>x.Name);
   for(int o=0;o<=b.Length-160;o+=4){
    int id=I(b,o),faction=I(b,o+4),compound=I(b,o+0x4c);if(faction<1||faction>24||compound<0||compound>1)continue;
    if(compound==0&&(id<1||id>24)||compound==1&&((id&65535)<1||(id&65535)>33||(id>>16)<1||(id>>16)>55))continue;
    if(I(b,o+0x54)<0||I(b,o+0x58)<=0||I(b,o+0x58)>10000000||I(b,o+0x54)>I(b,o+0x58)||I(b,o+0x74)<0||I(b,o+0x74)>3||I(b,o+0x78)<0||I(b,o+0x78)>2)continue;
    try {string name=Name(b,o+12);if(name.Length==0||compound==0&&name!=machines[id]||name.Any(c=>Char.IsControl(c)))continue;found.Add(new EquipmentRow{Table="save",Name=(faction==1?"[아군] ":"[세력 "+faction+"] ")+name+" · "+o.ToString("X"),Id=id,Offset=o,Fields=SavedFields});}catch(DecoderFallbackException){}catch(InvalidDataException){}
   }
   if(found.Count==0)throw new InvalidDataException("이 저장에서 확실하게 식별 가능한 장비가 없습니다.");
   SavePath=Path.GetFullPath(path);originalSave=b;SaveData=(byte[])b.Clone();Rows=found;
  }
  public string Save(){return Save(true);}
  public string Save(bool checkGame){
   if(checkGame)SaveModel.CheckGameClosed();string path=IsSave?SavePath:Path.Combine(DirectoryName,"patch104.pak");byte[] before=IsSave?originalSave:originalPatch;
   if(!File.ReadAllBytes(path).SequenceEqual(before))throw new IOException("열어 둔 이후 파일이 변경되었습니다. 다시 열어 주세요.");
   byte[] next;if(IsSave)next=SaveData;else {var output=new Dictionary<string,byte[]>(patch,StringComparer.OrdinalIgnoreCase);foreach(var t in Tables)if(!t.Value.SequenceEqual(originalTables[t.Key]))output[t.Key]=t.Value;next=WritePak(output);ReadPak(next);SaveProfile();}
   string dir=Path.Combine(Path.GetDirectoryName(path),"EquipmentEditorBackups");Directory.CreateDirectory(dir);string backup=Path.Combine(dir,Path.GetFileName(path)+"."+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff")+"."+Guid.NewGuid().ToString("N").Substring(0,8)+".bak");File.WriteAllBytes(backup,before);
   if(SaveModel.Hash(File.ReadAllBytes(backup))!=SaveModel.Hash(before))throw new IOException("장비 백업 검증에 실패했습니다.");File.WriteAllText(backup+".sha256",SaveModel.Hash(before),Encoding.ASCII);
   string tmp=path+"."+Guid.NewGuid().ToString("N")+".tmp";try {using(var stream=new FileStream(tmp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){stream.Write(next,0,next.Length);stream.Flush(true);}if(!File.ReadAllBytes(path).SequenceEqual(before))throw new IOException("저장 중 원본이 변경되었습니다.");File.Replace(tmp,path,null);}finally{if(File.Exists(tmp))File.Delete(tmp);}
   if(IsSave)originalSave=(byte[])SaveData.Clone();else {originalPatch=next;patch=ReadPak(next);foreach(var t in Tables)originalTables[t.Key]=(byte[])t.Value.Clone();}return backup;
  }
 }
}
