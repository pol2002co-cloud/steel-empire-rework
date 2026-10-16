using System;
using System.Runtime.InteropServices;
using System.Text;
class Probe {
 [DllImport("kernel32.dll")] static extern uint GetACP();
 [DllImport("user32.dll",CallingConvention=CallingConvention.Cdecl,ExactSpelling=true)] static extern int wsprintfA(byte[] output,byte[] format,byte[] value);
 [DllImport("kernel32.dll",SetLastError=true)] static extern int WideCharToMultiByte(uint cp,uint flags,byte[] wide,int count,byte[] result,int capacity,IntPtr replacement,IntPtr used);
 static void Main(){
  var text=Encoding.GetEncoding(949).GetBytes("마리에 보석지팡이 테스트\0");var buffer=new byte[512];
  int count=wsprintfA(buffer,new byte[]{37,115,0},text);
  Console.WriteLine("ACP="+GetACP()+" length="+count+" bytes="+BitConverter.ToString(buffer,0,count));
  Console.WriteLine("input="+BitConverter.ToString(text,0,text.Length-1));
  var wide=Encoding.Unicode.GetBytes("한글 선택창 테스트\0");
  int chars=wide.Length/2;
  foreach(uint cp in new uint[]{0,949}){
   var result=new byte[chars*2];int length=WideCharToMultiByte(cp,0,wide,-1,result,result.Length,IntPtr.Zero,IntPtr.Zero);
   Console.WriteLine("resource conversion cp="+cp+" count="+length+" bytes="+BitConverter.ToString(result,0,Math.Max(0,length)));
   if(cp==949){var expected=Encoding.GetEncoding(949).GetBytes("한글 선택창 테스트\0");if(length!=expected.Length)throw new Exception("CP949 length mismatch");for(int i=0;i<length;i++)if(result[i]!=expected[i])throw new Exception("CP949 bytes mismatch");}
  }
 }
}
