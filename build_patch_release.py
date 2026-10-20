"""Private build: no original game bytes or decoded assets enter the output tree."""
from pathlib import Path
import base64, hashlib, json, shutil, struct, subprocess, sys, zipfile
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]/'steel-rework'
GAME=Path('D:/Games/DGGL/Games/EoSteel_Win')
OUT=ROOT/'output'
VERSION='0.9.2'
CSC=Path('C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe')
sys.path.insert(0,str(WORK))
from archive import entries,decode

def sha(b):return hashlib.sha256(b).hexdigest()
def text(p,t):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8-sig')
def delta(a,b):
 assert len(b)>=len(a)
 runs=[];i=0
 while i<len(a):
  if a[i]==b[i]:i+=1;continue
  start=i
  while i<len(a) and a[i]!=b[i]:i+=1
  runs.append([start,base64.b64encode(bytes(x^y for x,y in zip(a[start:i],b[start:i]))).decode()])
 return dict(source_sha256=sha(a),target_sha256=sha(b),length=len(b),xor=runs,append=base64.b64encode(b[len(a):]).decode())
def unpack(pak):
 return {n:decode(pak[o:o+s]) if f else pak[o:o+s] for n,f,o,s,r in entries(pak)}
def build():
 OUT.mkdir(exist_ok=True);(OUT/'payload').mkdir(exist_ok=True)
 meta=json.loads((WORK/'manifest.json').read_text(encoding='utf-8'))
 original=next(p.read_bytes() for p in (GAME/'ReworkBackups').rglob('SteelEmpire.exe') if sha(p.read_bytes())==meta['source_sha256'])
 engine=(WORK/'package/SteelEmpire.exe').read_bytes();assert sha(engine)==meta['output_sha256']
 pak=(WORK/'package/patch104.pak').read_bytes();updated=unpack(pak)
 archives={};patches=[]
 for name,b in updated.items():
  archive='Data.pak' if name.endswith('.dat') else 'patch102.pak'
  raw=(GAME/archive).read_bytes();archives[archive]=sha(raw);source=unpack(raw)[name]
  patches.append(dict(name=name,archive=archive,delta=delta(source,b)))
 support=sorted({meta['source_sha256'],meta['output_sha256'],*[sha(p.read_bytes()) for p in WORK.glob('SteelEmpire-v*.exe')]})
 payload=['SteelRework.exe','SteelRework169.exe','SteelReworkQHD.exe','ddraw.dll','ddraw.ini','SteelCharacterEditor-사용법.txt','SteelRework169-사용법.txt']
 for name in payload:shutil.copy2(WORK/'package'/name,OUT/'payload'/name)
 # The editor no longer embeds the copyrighted character template table.
 src=(WORK/'editor/SaveModel.cs').read_text(encoding='utf-8-sig')
 begin=src.index('   using(var stream=typeof(SaveModel).Assembly.GetManifestResourceStream("char.dat")){')
 end=src.index('   for(int o=0;',begin)
 src=src[:begin]+'''   string templatePath=System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"ReworkCharacterTemplates.dat");
   if(!File.Exists(templatePath))throw new InvalidDataException("원본 게임 폴더에 패치를 먼저 설치해 주세요. 인물 기준 데이터가 필요합니다.");
   templates=File.ReadAllBytes(templatePath);
   if(templates.Length!=88744)throw new InvalidDataException("인물 기준 데이터 길이가 다릅니다.");
'''+src[end:]
 template_hash=next(x['delta']['source_sha256'] for x in patches if x['name']=='char.dat')
 src=src.replace('   if(templates.Length!=88744)', '   using(var hash=SHA256.Create()){if(BitConverter.ToString(hash.ComputeHash(templates)).Replace("-","").ToLowerInvariant()!="'+template_hash+'")throw new InvalidDataException("인물 기준 데이터 검증에 실패했습니다. 패치를 다시 설치해 주세요.");}\n   if(templates.Length!=88744)')
 source=ROOT/'source';source.mkdir(exist_ok=True)
 text(source/'SaveModel.cs',src);shutil.copy2(WORK/'editor/Editor.cs',source/'Editor.cs')
 subprocess.run([str(CSC),'/nologo','/target:winexe','/platform:x86','/optimize+', '/out:'+str(OUT/'payload/SteelCharacterEditor.exe'),'/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Core.dll',str(source/'SaveModel.cs'),str(source/'Editor.cs')],check=True)
 payload.append('SteelCharacterEditor.exe')
 manifest=dict(version=VERSION,gameplay_version='0.9.1',engine=delta(original,engine),archives=archives,entries=patches,pak_sha256=sha(pak),supported_executable_hashes=support,payload={n:sha((OUT/'payload'/n).read_bytes()) for n in payload})
 text(OUT/'patch-manifest.json',json.dumps(manifest,ensure_ascii=False,separators=(',',':')))
 for name in ['Install-Patch.ps1','PatchEngine.cs']:text(OUT/name,(ROOT/name).read_text(encoding='utf-8-sig'))
 (OUT/'Install-Patch.cmd').write_text('@echo off\r\npowershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Install-Patch.ps1"\r\npause\r\n',encoding='ascii')
 restore=(ROOT.parent/'Restore-Update.ps1').read_text(encoding='utf-8-sig').replace("'patch104.pak',","'patch104.pak','ReworkCharacterTemplates.dat',")
 restore=restore.replace("$ErrorActionPreference='Stop'", "$ErrorActionPreference='Stop'\nImport-Module (Join-Path $PSHOME 'Modules\\Microsoft.PowerShell.Utility\\Microsoft.PowerShell.Utility.psd1') -Force")
 text(OUT/'Restore-Patch.ps1',restore)
 third=OUT/'third-party';third.mkdir(exist_ok=True)
 shutil.copy2(ROOT.parent/'third-party/cnc-ddraw-LICENSE.txt',third/'cnc-ddraw-LICENSE.txt')
 text(OUT/'README.md',README)
 docs=OUT/'docs';docs.mkdir(exist_ok=True)
 for name in ['CHANGELOG.md','확장캠페인-v090-사용법.txt','보스-아군배치-수정-v091.txt']:
  body=(ROOT.parent/'docs'/name).read_text(encoding='utf-8-sig')
  if name=='CHANGELOG.md':body=body.replace('과거 실행 파일 스냅샷은 소스 ZIP의 역사 자료이며 단독 교체용 설치 패키지가 아닙니다.','원본 실행 파일·게임 데이터·과거 실행 파일 스냅샷은 공개 배포하지 않습니다.')
  text(docs/name,body)
 # Strict allowlist: do not copy previous source bundles, extracted scripts, binaries or dumps.
 public=ROOT/'public-source';public.mkdir(exist_ok=True)
 shutil.copy2(OUT/'README.md',public/'README.md')
 for name in ['PatchEngine.cs','Install-Patch.ps1']:shutil.copy2(OUT/name,public/name)
 shutil.copy2(OUT/'Install-Patch.cmd',public/'Install-Patch.cmd')
 for p in source.glob('*.cs'):shutil.copy2(p,public/p.name)
 for name in ['Launcher.cs','WideLauncher.cs','WideLauncherQHD.cs'] :shutil.copy2(WORK/name,public/name)
 shutil.copy2(OUT/'Restore-Patch.ps1',public/'Restore-Patch.ps1')
 # Build tooling is useful, but requires the developer's private, owned game inputs.
 shutil.copy2(Path(__file__),public/'build_patch_release.py')
 assets=ROOT/'assets';assets.mkdir(exist_ok=True)
 paths=[(f'SteelEmpire-Rework-v{VERSION}-PatchOnly.zip',OUT),(f'SteelEmpire-Rework-v{VERSION}-PatchSource.zip',public)]
 for name,folder in paths:
  with zipfile.ZipFile(assets/name,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for p in sorted(folder.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(folder).as_posix())
  with zipfile.ZipFile(assets/name) as z:assert z.testzip() is None
 text(assets/'SHA256SUMS.txt',''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(assets.glob('*.zip'))))
 text(ROOT/'build-report.json',json.dumps({p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in assets.iterdir()},indent=2))
 print((ROOT/'build-report.json').read_text(encoding='utf-8-sig'))

README='''# 강철제국 리워크 — 원본 보유자용 패치 v0.9.2

게임 기능은 v0.9.1과 같습니다. v0.9.2는 배포 방식을 변경한 버전입니다.
원본 게임 전체, 원본·수정 게임 실행 파일, PAK, 음악, 영상, 추출 데이터와
개인 저장 파일은 다운로드에 포함하지 않습니다. 이 파일만으로 게임을 실행할 수 없습니다.

## 설치

1. 본인이 보유한 원본 강철제국 Windows판을 별도 폴더에 설치합니다.
2. PatchOnly ZIP을 게임 폴더와 다른 폴더에 완전히 풉니다.
3. 게임·런처·인물 에디터를 종료합니다.
4. Install-Patch.cmd를 더블클릭하고 원본 게임 설치 폴더를 선택합니다.

명령으로 설치하려면 Windows PowerShell에서 아래 경로를 바꿔 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\Install-Patch.ps1 -GamePath "D:\\Games\\DGGL\\Games\\EoSteel_Win"
```

검증된 원본 실행 파일과 Data.pak·patch102.pak가 필요합니다. 다른 판본은 임의로
수정하지 않고 중단합니다. 기존 리워크 사용자는 ReworkBackups에 검증된 원본 실행 파일이
남아 있으면 적용할 수 있습니다. 없다면 본인 원본 설치본에서 확보해야 합니다.
원본 실행 파일 SHA256: 65bf8699804849f36cef9108eebe88f8c9f1661ac77ea5c2e6688ae347795fde

설치 도구는 원본의 기존 바이트를 읽고 XOR 변경분·추가 코드를 적용하여 실행 파일을
생성합니다. 게임 데이터도 원본 PAK에서 읽은 항목에 변경분을 적용하여 patch104.pak를
생성합니다. 생성 결과는 v0.9.1 실행 파일·데이터 팩과 바이트 단위로 동일합니다.
인물 에디터용 기준 데이터도 사용자 PC에서 생성하며 에디터에는 내장하지 않습니다.
ReworkCharacterTemplates.dat는 에디터 옆에 유지하고 재배포하지 마세요.

원본은 ReworkBackups에 백업합니다. 기존 저장과 ddraw.ini 설정은 유지합니다.
설치 후 SteelRework.exe 또는 SteelReworkQHD.exe를 실행하세요.
게임 폴더 전체나 설치 후 생성된 게임 파일을 다른 사람에게 보내지 말고, 원본이
없는 PatchOnly ZIP 또는 최신 릴리스 링크를 공유하세요.

## 복원

게임·런처·에디터 종료 후 새로 생성된 ReworkBackups/v0.9.2-delta-날짜 폴더의
Restore-Patch.ps1을 PowerShell로 실행합니다. 원래 존재하던 파일을 복구하고
이번에 추가한 파일을 제거합니다. 저장은 복원하지 않습니다. 구버전 복귀 전
저장 파일도 별도로 백업하세요.

## 기능과 검증 범위

기존 누적 패치·F8 이벤트 창·F9 특수병기 제작·경험치·본거지·호환성 기능을 유지합니다.
상세 내역은 docs를 참조하세요. 모든 이야기 분기를 실제 플레이로 완주한 버전은 아닙니다.
원본 보유 여부를 법적으로 인증하는 DRM은 아니며, 지원 원본 파일 해시를 확인합니다.

## 권리

원본 게임·명칭·제3자 구성요소의 권리는 각 권리자에게 있습니다. 비공식 수정 패치입니다.
원본을 포함하지 않는 형식으로 전환한 것이며, 수정·배포에 관한 모든 법적 쟁점이
자동으로 해소된다는 의미는 아닙니다. 기존에 받은 허가의 범위를 준수하세요.
cnc-ddraw는 별도 MIT 라이선스를 따르며 고지는 third-party에 포함합니다.
원본 게임에 MIT 등 새 라이선스를 부여하지 않습니다.

## 소스

PatchSource는 원본 데이터 없는 설치 엔진과 런처·에디터의 C# 코드입니다.
인물 에디터를 빌드할 때 원본 char.dat를 리소스로 넣지 마세요.
배포 변경분은 patch-manifest.json에 있으며, 기계어 함수·데이터 변경을 포함합니다.
원본 게임 C/C++ 소스와 게임 데이터는 제공하지 않습니다.
'''
if __name__=='__main__':build()
