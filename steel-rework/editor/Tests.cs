using System;using System.IO;using System.Linq;using System.Collections.Generic;using SteelEditor;
class Tests {
 static int checks;static void Check(bool b,string name){if(!b)throw new Exception(name);checks++;Console.WriteLine("PASS "+name);}
 static void Reject(Action a,string name){bool rejected=false;try{a();}catch{rejected=true;}Check(rejected,name);}
 static void Main(string[] args){string root=Path.GetFullPath(args[1]);Directory.CreateDirectory(root);
 foreach(string source in Directory.GetFiles(args[0],"*.Sav")){
  byte[] original=File.ReadAllBytes(source);string path=Path.Combine(root,Path.GetFileName(source));File.WriteAllBytes(path,original);var m=new SaveModel(path);
  Check(m.People.Count>0&&!m.Dirty,"parse "+Path.GetFileName(path)+" people="+m.People.Count);
  var p=m.People.First(x=>x.Companion);m.Apply(p,new Dictionary<int,int>(),-1);Check(!m.Dirty,"no-op identical");
  int level=m.Get(p,0x48)==99?98:m.Get(p,0x48)+1;m.Apply(p,new Dictionary<int,int>{{0x48,level}},-1);
  Check(p.Copies.All(o=>SaveModel.I(m.Data,o+0x48)==level),"all formation copies updated");
  var allowed=new HashSet<int>(p.Copies.SelectMany(o=>Enumerable.Range(o+0x48,4)));Check(Enumerable.Range(0,original.Length).All(i=>allowed.Contains(i)||original[i]==m.Data[i]),"only selected field bytes changed");
  m.Reset(p);Check(!m.Dirty,"reset exact original");
  var extended=new Dictionary<int,int>{{0x74,17},{0x78,23},{0x7c,m.Get(p,0x7c)^31},{0x80,m.Get(p,0x80)^255}};
  m.Apply(p,extended,-1);Check(p.Copies.All(o=>extended.All(v=>SaveModel.I(m.Data,o+v.Key)==v.Value)),"army bonuses and named abilities in every copy");
  var extendedBytes=new HashSet<int>(p.Copies.SelectMany(o=>extended.Keys.SelectMany(k=>Enumerable.Range(o+k,4))));
  Check(Enumerable.Range(0,original.Length).All(i=>extendedBytes.Contains(i)||original[i]==m.Data[i]),"extended edits preserve all other bytes");m.Reset(p);
  Reject(()=>m.Apply(p,new Dictionary<int,int>{{0x7c,m.Get(p,0x7c)^256}},-1),"unknown ability flags preserved");
  var outside=m.People.FirstOrDefault(x=>x.Outside);if(outside!=null){int value=m.Get(outside,0x48)==99?98:m.Get(outside,0x48)+1;m.Apply(outside,new Dictionary<int,int>{{0x48,value}},-1);Check(outside.Copies.All(o=>SaveModel.I(m.Data,o+0x48)==value),"NPC outside Forum editable");m.Reset(outside);}
  Reject(()=>m.Apply(p,new Dictionary<int,int>{{0x54,99999},{0x58,1}},-1),"HP validation");
  var assigned=m.People.FirstOrDefault(x=>x.Companion&&!m.CanState(x));if(assigned!=null)Reject(()=>m.Apply(assigned,new Dictionary<int,int>(),1),"assigned state rejected");
  var free=m.People.FirstOrDefault(x=>m.CanState(x));if(free!=null){m.Apply(free,new Dictionary<int,int>(),1);Check(m.Get(free,4)==1&&m.Get(free,0x54)==0,"death state");m.Apply(free,new Dictionary<int,int>{{0x54,m.Get(free,0x58)}},0);Check(m.Get(free,4)==0&&m.Get(free,0x54)>0,"revive state");m.Reset(free);}
  m.Apply(p,new Dictionary<int,int>{{0x48,level}},-1);string backup=m.Save(path,false);Check(File.ReadAllBytes(backup).SequenceEqual(original),"backup exact");Check(new SaveModel(path).Get(new SaveModel(path).People.First(x=>x.Companion),0x48)==level,"saved reload");
  m.Restore(backup);Check(File.ReadAllBytes(path).SequenceEqual(original),"restore exact");
  File.WriteAllBytes(path,original.Concat(new byte[]{0}).ToArray());Reject(()=>m.Save(path,false),"external change rejected");File.WriteAllBytes(path,original);
  Check(File.ReadAllBytes(source).SequenceEqual(original),"user save untouched");
 }
 string bad=Path.Combine(root,"invalid.sav");File.WriteAllBytes(bad,new byte[2048]);Reject(()=>new SaveModel(bad),"unknown format rejected");Console.WriteLine("TOTAL "+checks);
 }
}
