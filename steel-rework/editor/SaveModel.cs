using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Diagnostics;

namespace SteelEditor {
 public sealed class Stat {
  public int Offset, Min, Max; public string Name;
  public Stat(int o,string n,int min,int max){Offset=o;Name=n;Min=min;Max=max;}
 }
 public sealed class Person {
  public int Id,Offset; public string Name; public bool Companion, Outside;
  public List<int> Copies=new List<int>();
  public override string ToString(){return Name;}
 }
 public sealed class SaveModel {
  public static readonly Stat[] Stats={
   new Stat(0x48,"레벨",1,99),new Stat(0x54,"현재 HP",0,99999),
   new Stat(0x58,"최대 HP",1,99999),new Stat(0x4c,"현재 경험치",0,9999999),
   new Stat(0x50,"다음 레벨 필요 경험치",1,9999999),new Stat(0x60,"명중",0,9999),
   new Stat(0x5c,"방어",0,9999),new Stat(0x64,"회피",0,9999),new Stat(0x70,"기량",0,9999),
   new Stat(0x74,"군단 공격 보정",-100,100),new Stat(0x78,"군단 방어 보정",-100,100)
  };
  public static readonly string[] Leadership={"격려","회복","질타","노호","현혹"};
  public static readonly string[] Specials={"저력","저격","재생","행운","댄스","정비","건축","과학"};
  public static readonly string[] Classes={"없음","동원병","경보병","중보병","장갑척탄병","해병","장갑보병","중장갑보병","과학자","파일럿","드라이버","기술자","건축가","댄서"};
  public string PathName; public byte[] Original,Data; public List<Person> People;
  static readonly Encoding Korean=Encoding.GetEncoding(949,EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback);
  public static int I(byte[] b,int o){if(o<0||o>b.Length-4)throw new InvalidDataException("저장 파일이 잘렸습니다.");return BitConverter.ToInt32(b,o);}
  static void W(byte[] b,int o,int v){Buffer.BlockCopy(BitConverter.GetBytes(v),0,b,o,4);}
  static string NameAt(byte[] b,int o,int len){int n=Array.IndexOf(b,(byte)0,o,len);if(n<0)throw new InvalidDataException("인물 이름 형식이 다릅니다.");return Korean.GetString(b,o,n-o);}
  static bool Valid(byte[] b,int p,int kind){
   if(p<0||p>b.Length-168)return false;
   if(I(b,p)<1||I(b,p)>255||I(b,p+8)!=kind||I(b,p+4)<0||I(b,p+4)>2)return false;
   if(I(b,p+0x38)<1||I(b,p+0x38)>13||I(b,p+0x48)<1||I(b,p+0x48)>99)return false;
   if(I(b,p+0x10)<0||I(b,p+0x10)>15||I(b,p+0x14)<0||I(b,p+0x14)>24)return false;
   return I(b,p+0x58)>0 && I(b,p+0x58)<=10000000;
  }
  static int Count(byte[] b,ref int q,int max){int n=I(b,q);q+=4;if(n<0||n>max)throw new InvalidDataException("지원하지 않는 저장 목록 구조입니다.");return n;}
  static List<Person> Parse(byte[] b){
   if(b.Length<1024||b.Length>64*1024*1024||I(b,0)!=0x12)throw new InvalidDataException("지원하는 강철제국 저장 파일이 아닙니다.");
   var candidates=new List<List<Person>>();
   // Town serializer 0x435e30: 0xd4 header, 0x10 facility metadata,
   // six counted DWORD lists, counted 0xa8 companion records, mercenary list.
   for(int p=0;p<b.Length-232;p+=4){
    if(I(b,p)!=1||I(b,p+4)!=1)continue;
    try {
     if(NameAt(b,p+52,32)!="포룸")continue;
     int q=p+228;
     for(int j=0;j<6;j++){int n=Count(b,ref q,4096);q=checked(q+n*4);if(q>b.Length-4)throw new InvalidDataException();}
     var people=new List<Person>();int named=Count(b,ref q,255);if(named<1)continue;
     for(int j=0;j<named;j++,q+=168){
      if(!Valid(b,q,3))throw new InvalidDataException();
      people.Add(new Person{Id=I(b,q),Name=NameAt(b,q+24,32),Offset=q,Companion=true});
     }
     if(people.Select(x=>x.Id).Distinct().Count()!=named)throw new InvalidDataException();
     int generic=Count(b,ref q,10000);
     for(int j=0;j<generic;j++,q+=168){
      if(!Valid(b,q,1))throw new InvalidDataException();
      people.Add(new Person{Id=I(b,q),Name=NameAt(b,q+24,32),Offset=q,Companion=false});
     }
     if(q>b.Length)throw new InvalidDataException();
     foreach(var c in people){
      c.Copies.Add(c.Offset);
      if(!c.Companion)continue;
      // Formation copies refer back to the master companion by ID during load.
      // Match the full 32-byte name, type, class, and validated record fields.
      for(int o=0;o<b.Length-167;o+=4){
       if(o==c.Offset||I(b,o)!=c.Id||I(b,o+8)!=3||I(b,o+0x38)!=I(b,c.Offset+0x38))continue;
       if(!Valid(b,o,3))continue;
       bool equal=true;for(int k=0;k<32;k++)if(b[o+24+k]!=b[c.Offset+24+k]){equal=false;break;}
       if(equal)c.Copies.Add(o);
      }
     }
     candidates.Add(people);
    }catch(InvalidDataException){}catch(DecoderFallbackException){}catch(ArgumentException){}catch(OverflowException){}
   }
   if(candidates.Count!=1)throw new InvalidDataException("플레이어 인물 명단을 확실하게 식별하지 못했습니다. 이 저장 파일은 수정하지 않습니다.");
   var result=candidates[0];
   // Exact template names prevent incidental integers in other records from
   // being mistaken for characters. Only existing serialized NPCs are edited.
   byte[] templates;
   using(var stream=typeof(SaveModel).Assembly.GetManifestResourceStream("char.dat")){
    if(stream==null)throw new InvalidDataException("인물 기준 데이터가 없습니다.");
    templates=new byte[stream.Length];int read=0;while(read<templates.Length){int n=stream.Read(templates,read,templates.Length-read);if(n==0)throw new EndOfStreamException();read+=n;}
   }
   for(int o=0;o<b.Length-167;o+=4){
    if(!Valid(b,o,3))continue;
    int id=I(b,o);if(id<14||result.Any(x=>x.Companion&&x.Id==id))continue;
    try{
     string name=NameAt(b,o+24,32);
     if(name!=NameAt(templates,4+(id-1)*348+8,32))continue;
     var p=new Person{Id=id,Name=name,Offset=o,Companion=true,Outside=true};
     for(int q=o;q<b.Length-167;q+=4){
      if(!Valid(b,q,3)||I(b,q)!=id||I(b,q+0x38)!=I(b,o+0x38))continue;
      if(Enumerable.Range(0,32).All(k=>b[q+24+k]==b[o+24+k]))p.Copies.Add(q);
     }
     result.Add(p);
    }catch(DecoderFallbackException){}catch(InvalidDataException){}
   }
   return result;
  }
  public SaveModel(string path){PathName=Path.GetFullPath(path);Original=File.ReadAllBytes(PathName);Data=(byte[])Original.Clone();People=Parse(Data);}
  public int Get(Person c,int off){return I(Data,c.Offset+off);}
  public string ClassName(Person c){int x=Get(c,0x38);return x<Classes.Length?Classes[x]:"병과 "+x;}
  public string State(Person c){int s=Get(c,4);if(s==1)return "사망 / 복귀 대기";if(s==2)return "훈련·전직 중";if(Get(c,0x54)==0)return "HP 0 (상태 유지)";return Get(c,0x10)>0||Get(c,0x14)>0?"생존 · 배치 중":"생존 · 대기";}
  public string StateRestriction(Person c){
   if(!c.Companion)return "일반 용병은 능력치만 수정합니다. 사망하면 삭제되는 게임 규칙을 유지합니다.";
   if(Get(c,4)==2)return "훈련·전직 완료 후 저장하고 다시 열면 상태를 변경할 수 있습니다.";
   if(Get(c,0x10)!=0||Get(c,0x14)!=0||c.Copies.Count>1)return "부대·보직·훈련에서 해제한 뒤 게임에서 저장하고 다시 열어 주세요. 현재 인물의 능력치는 수정할 수 있습니다.";
   return c.Outside?"포룸 밖 인물입니다. 사망 상태를 변경해도 자동으로 동료가 되지는 않습니다.":"사망은 복귀 대기 상태입니다. 기존 리워크에서는 다음 날 자정에 돌아옵니다.";
  }
  public bool CanState(Person c){return c.Companion&&Get(c,4)!=2&&Get(c,0x10)==0&&Get(c,0x14)==0&&c.Copies.Count==1;}
  public bool Dirty{get{return !Original.SequenceEqual(Data);}}
  public int ChangedCount{get{return People.Count(c=>c.Copies.Any(o=>!Original.Skip(o).Take(168).SequenceEqual(Data.Skip(o).Take(168))));}}
  public void Apply(Person c,Dictionary<int,int> values,int state){
   if(!People.Contains(c))throw new InvalidOperationException("다른 저장 파일의 인물입니다.");
   foreach(var v in values){
    if(v.Key==0x7c||v.Key==0x80){int mask=v.Key==0x7c?31:255;if((v.Value&~mask)!=(Get(c,v.Key)&~mask))throw new InvalidDataException("알 수 없는 능력 비트는 변경할 수 없습니다.");continue;}
    var s=Stats.FirstOrDefault(x=>x.Offset==v.Key);if(s==null||v.Value<s.Min||v.Value>s.Max)throw new InvalidDataException("능력치가 허용 범위를 벗어났습니다.");
   }
   int hp=values.ContainsKey(0x54)?values[0x54]:Get(c,0x54),max=values.ContainsKey(0x58)?values[0x58]:Get(c,0x58);
   if(hp>max)throw new InvalidDataException("현재 HP는 최대 HP보다 클 수 없습니다.");
   if(state< -1||state>1)throw new InvalidDataException("지원하지 않는 인물 상태입니다.");
   if(state!=-1&&!CanState(c))throw new InvalidOperationException(StateRestriction(c));
   if(state==0&&hp==0)throw new InvalidDataException("생존으로 변경하려면 현재 HP를 1 이상으로 설정해 주세요.");
   byte[] next=(byte[])Data.Clone();
   foreach(int o in c.Copies){foreach(var v in values)W(next,o+v.Key,v.Value);if(state!=-1){W(next,o+4,state);W(next,o+0x54,state==1?0:hp);}}
   Parse(next);Data=next;
  }
  public void Reset(Person c){foreach(int o in c.Copies)Buffer.BlockCopy(Original,o,Data,o,168);}
  public static string Hash(byte[] b){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","");}
  public static void CheckGameClosed(){if(Process.GetProcessesByName("SteelEmpire").Length!=0)throw new IOException("게임을 완전히 종료한 뒤 저장해 주세요. 게임의 저장 덮어쓰기를 방지합니다.");}
  public string Save(string destination,bool checkGame){
   if(checkGame)CheckGameClosed();
   string dest=Path.GetFullPath(destination);Parse(Data);
   if(!File.ReadAllBytes(PathName).SequenceEqual(Original))throw new IOException("열어 둔 이후 원본 저장 파일이 변경되었습니다. 다시 열어 주세요.");
   bool same=String.Equals(dest,PathName,StringComparison.OrdinalIgnoreCase);
   if(!same&&File.Exists(dest))throw new IOException("다른 이름 저장은 새 파일명으로 해주세요. 기존 저장 파일은 덮어쓰지 않습니다.");
   string dir=Path.GetDirectoryName(dest),backupDir=Path.Combine(dir,"EditorBackups");Directory.CreateDirectory(backupDir);
   string backup=Path.Combine(backupDir,Path.GetFileName(PathName)+"."+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff")+"."+Guid.NewGuid().ToString("N").Substring(0,8)+".bak");
   // Exact original bytes and a digest are retained before any replacement.
   File.WriteAllBytes(backup,Original);if(Hash(File.ReadAllBytes(backup))!=Hash(Original))throw new IOException("백업 검증에 실패했습니다.");
   File.WriteAllText(backup+".sha256",Hash(Original),Encoding.ASCII);
   string tmp=Path.Combine(dir,".steel-editor-"+Guid.NewGuid().ToString("N")+".tmp");
   try {
    using(var f=new FileStream(tmp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(Data,0,Data.Length);f.Flush(true);}
    if(!File.ReadAllBytes(PathName).SequenceEqual(Original))throw new IOException("저장 중 원본 파일이 변경되었습니다. 덮어쓰기를 취소했습니다.");
    if(same)File.Replace(tmp,dest,null);else File.Move(tmp,dest);
   }finally{if(File.Exists(tmp))File.Delete(tmp);}
   PathName=dest;Original=(byte[])Data.Clone();return backup;
  }
  public string Restore(string backup){
   CheckGameClosed();var restored=File.ReadAllBytes(backup);Parse(restored);
   if(!File.Exists(backup+".sha256")||File.ReadAllText(backup+".sha256").Trim()!=Hash(restored))throw new IOException("에디터가 만든 검증 가능한 백업만 복원합니다.");
   byte[] before=Data;Data=restored;
   try{string result=Save(PathName,true);People=Parse(Data);return result;}catch{Data=before;throw;}
  }
 }
}
