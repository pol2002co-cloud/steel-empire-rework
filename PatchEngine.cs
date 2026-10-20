using System;
using System.IO;
using System.Text;
using System.Collections;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;

// Only differences are shipped. All unchanged game bytes come from the user's copy.
public static class PatchEngine {
 public static string Hash(byte[] b){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant();}
 static int Num(object o){return Convert.ToInt32(o);}
 static Dictionary<string,object> Obj(object o){return (Dictionary<string,object>)o;}
 static byte[] Apply(byte[] original,Dictionary<string,object> d){
  if(Hash(original)!=(string)d["source_sha256"])throw new InvalidDataException("Unsupported original file.");
  int length=Num(d["length"]);if(length<original.Length||length>16000000)throw new InvalidDataException("Invalid delta length.");
  byte[] result=new byte[length];Buffer.BlockCopy(original,0,result,0,original.Length);
  int end=0;
  foreach(object entry in (IEnumerable)d["xor"]){
   var row=(IList)entry;int offset=Num(row[0]);byte[] value=Convert.FromBase64String((string)row[1]);
   if(offset<end||offset>original.Length-value.Length)throw new InvalidDataException("Invalid XOR range.");
   for(int i=0;i<value.Length;i++)result[offset+i]^=value[i];end=offset+value.Length;
  }
  byte[] tail=Convert.FromBase64String((string)d["append"]);
  if(tail.Length!=length-original.Length)throw new InvalidDataException("Invalid append length.");
  Buffer.BlockCopy(tail,0,result,original.Length,tail.Length);
  if(Hash(result)!=(string)d["target_sha256"])throw new InvalidDataException("Reconstructed file failed verification.");return result;
 }
 static byte[] Extract(byte[] pak,string wanted){
  if(pak.Length<9)throw new InvalidDataException("Invalid archive.");
  int pos=BitConverter.ToInt32(pak,pak.Length-9),count=BitConverter.ToInt32(pak,pak.Length-5);
  if(pos<0||count<0||count>10000)throw new InvalidDataException("Invalid archive index.");
  for(int i=0;i<count;i++){
   if(pos>pak.Length-15)throw new InvalidDataException("Truncated archive index.");
   int n=pak[pos],flag=pak[pos+1],offset=BitConverter.ToInt32(pak,pos+2),size=BitConverter.ToInt32(pak,pos+6),raw=BitConverter.ToInt32(pak,pos+10);
   if(n>pak.Length-pos-15||offset<0||size<0||offset>pak.Length-size||raw<0||raw>16000000)throw new InvalidDataException("Invalid archive entry.");
   string name=Encoding.GetEncoding(949).GetString(pak,pos+14,n);pos+=15+n;if(name!=wanted)continue;
   if(flag==0){if(size!=raw)throw new InvalidDataException("Invalid raw length.");byte[] b=new byte[raw];Buffer.BlockCopy(pak,offset,b,0,raw);return b;}
   var output=new List<byte>(raw);int p=offset,stop=offset+size;
   while(p<stop){int flags=pak[p++];for(int bit=0;bit<8&&p<stop;bit++){
    if((flags&(1<<bit))!=0){if(p+1>=stop)throw new InvalidDataException("Truncated compressed data.");int x=pak[p]|pak[p+1]<<8;p+=2;int distance=x&4095,length=(x>>12)+2;
     if(distance==0||distance>output.Count||length>raw-output.Count)throw new InvalidDataException("Invalid compressed reference.");
     for(int j=0;j<length;j++)output.Add(output[output.Count-distance]);
    }else{if(output.Count>=raw)throw new InvalidDataException("Oversized archive entry.");output.Add(pak[p++]);}
   }}if(output.Count!=raw)throw new InvalidDataException("Invalid decoded size.");return output.ToArray();
  }throw new InvalidDataException("Required original archive entry is missing: "+wanted);
 }
 public static void Generate(string game,string originalExe,string manifestPath,string stage){
  var js=new JavaScriptSerializer();js.MaxJsonLength=16000000;
  var manifest=js.Deserialize<Dictionary<string,object>>(File.ReadAllText(manifestPath,Encoding.UTF8));
  byte[] engine=Apply(File.ReadAllBytes(originalExe),Obj(manifest["engine"]));
  var archives=new Dictionary<string,byte[]>();
  foreach(var entry in Obj(manifest["archives"])){
   byte[] b=File.ReadAllBytes(Path.Combine(game,entry.Key));if(Hash(b)!=(string)entry.Value)throw new InvalidDataException("Unsupported original archive: "+entry.Key);archives[entry.Key]=b;
  }
  var files=new List<KeyValuePair<string,byte[]>>();byte[] templates=null;
  foreach(object value in (IEnumerable)manifest["entries"]){var d=Obj(value);string name=(string)d["name"];
   byte[] source=Extract(archives[(string)d["archive"]],name);if(name=="char.dat")templates=source;
   files.Add(new KeyValuePair<string,byte[]>(name,Apply(source,Obj(d["delta"]))));
  }
  byte[] pack;
  using(var body=new MemoryStream())using(var index=new MemoryStream()){
   var bw=new BinaryWriter(body);var ix=new BinaryWriter(index);
   foreach(var f in files){byte[] name=Encoding.GetEncoding(949).GetBytes(f.Key);ix.Write((byte)name.Length);ix.Write((byte)0);ix.Write((int)body.Length);ix.Write(f.Value.Length);ix.Write(f.Value.Length);ix.Write(name);ix.Write((byte)0);bw.Write(f.Value);}
   int offset=(int)body.Length;bw.Write(index.ToArray());bw.Write(offset);bw.Write(files.Count);bw.Write((byte)0x12);pack=body.ToArray();
  }
  if(Hash(pack)!=(string)manifest["pak_sha256"]||templates==null)throw new InvalidDataException("Generated data pack failed verification.");
  Directory.CreateDirectory(stage);File.WriteAllBytes(Path.Combine(stage,"SteelEmpire.exe"),engine);File.WriteAllBytes(Path.Combine(stage,"patch104.pak"),pack);File.WriteAllBytes(Path.Combine(stage,"ReworkCharacterTemplates.dat"),templates);
 }
}
