"""Private build: no original game bytes or decoded assets enter the output tree."""
from pathlib import Path
import base64, hashlib, json, shutil, struct, subprocess, sys, zipfile
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]/'steel-rework'
GAME=Path('C:/Games/DGGL/Games/EoSteel_Win')
VERSION='0.17.0'
VERSION_TAG='v'+VERSION.replace('.','')
OUT=ROOT/('output-'+VERSION_TAG)
WORLD_GUIDE='연간행사·전설설계도-v0170-사용법.txt'
OWN_CS_SOURCES=('SaveModel.cs','Editor.cs','EquipmentModel.cs','EquipmentEditor.cs','UpdateLauncher.cs')
WORLD_EVENT_SOURCES=('world_event_catalog.py','world_event_simple_catalog.py','world_event_state.py','world_event_actions.py','world_event_compile.py','world_events_patch.py','world_event_native.c','test_world_event_catalog.py','test_world_event_simple_catalog.py','test_world_event_simple.py','test_goal_occupation.py','test_world_event_state.py','test_world_event_actions.py','test_world_event_compile.py','test_world_events_patch.py','test_world_events_native.py','test_world_event_integration.py','world_tour_actions.py','test_world_tour_actions.py','test_world_tour.py','test_world_event_notifications.py','world_event_dispatch.py','test_world_event_dispatch.py','test_world_event_queue.py','retraining_notice_patch.py','test_retraining_notice.py','expedition_actions.py','expedition_storage.py','expedition_storage.h','expedition_native.c','expedition_catalog.py','ruin_visits.py','test_expedition_actions.py','test_expedition_storage.py','test_expedition_catalog.py','test_ruin_visits.py','test_expedition_native.py','test_expedition_save.py','test_expedition_reset.py','test_ruin_random.py','test_quest_usability.py','test_expedition_usability.py','test_expedition_auto.py','ruin_guardians.py','test_ruin_guardians.py','test_ruin_guardian_actions.py','quest_encounters.py','quest_encounters.c','test_quest_encounters.py','quest_art.py','quest_art_atlas.png','test_quest_art.py','test_quest_variety.py','seasonal_rewards_patch.py','legend_machines.py','legend_machine_atlas.png','test_monthly_world.py','test_monthly_rewards.py','test_legend_machines.py','test_legend_blueprints.py','xp_share_patch.py','campaign_patch.py')
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
 assert 'CurrentVersion="'+VERSION+'"' in (WORK/'launcher/UpdateLauncher.cs').read_text(encoding='utf-8-sig')
 subprocess.run([str(CSC),'/nologo','/target:winexe','/platform:x86','/optimize+',
                 '/out:'+str(WORK/'launcher/SteelReworkLauncher.exe'),'/r:System.Windows.Forms.dll',
                 '/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.IO.Compression.dll',
                 '/r:System.IO.Compression.FileSystem.dll',str(WORK/'launcher/UpdateLauncher.cs')],check=True)
 payload=['SteelRework.exe','SteelRework169.exe','SteelReworkQHD.exe','ddraw.dll','ddraw.ini','SteelCharacterEditor-사용법.txt','SteelRework169-사용법.txt']
 for name in payload:shutil.copy2(WORK/'package'/name,OUT/'payload'/name)
 for folder,names in [(WORK/'launcher',['SteelReworkLauncher.exe','SteelReworkLauncher-사용법.txt']),
                      (WORK/'editor',['SteelEquipmentEditor-사용법.txt'])]:
  for name in names:
   shutil.copy2(folder/name,OUT/'payload'/name);payload.append(name)
 shutil.copy2(WORK/'editor/SteelCharacterEditor-사용법.txt',OUT/'payload/SteelCharacterEditor-사용법.txt')
 for name in (WORLD_GUIDE,'QuestScenes.sqa'):
  shutil.copy2(WORK/name,OUT/'payload'/name);payload.append(name)
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
 source=ROOT/('source-'+VERSION_TAG);source.mkdir(exist_ok=True)
 text(source/'SaveModel.cs',src);shutil.copy2(WORK/'editor/Editor.cs',source/'Editor.cs')
 for name in ['EquipmentModel.cs','EquipmentEditor.cs']:shutil.copy2(WORK/'editor'/name,source/name)
 shutil.copy2(WORK/'launcher/UpdateLauncher.cs',source/'UpdateLauncher.cs')
 subprocess.run([str(CSC),'/nologo','/target:winexe','/platform:x86','/optimize+', '/out:'+str(OUT/'payload/SteelCharacterEditor.exe'),'/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Core.dll',str(source/'SaveModel.cs'),str(source/'Editor.cs')],check=True)
 payload.append('SteelCharacterEditor.exe')
 subprocess.run([str(CSC),'/nologo','/target:winexe','/platform:x86','/optimize+', '/out:'+str(OUT/'payload/SteelEquipmentEditor.exe'),'/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Core.dll',str(source/'SaveModel.cs'),str(source/'EquipmentModel.cs'),str(source/'EquipmentEditor.cs')],check=True)
 payload.append('SteelEquipmentEditor.exe')
 manifest=dict(version=VERSION,gameplay_version=VERSION,engine=delta(original,engine),archives=archives,entries=patches,pak_sha256=sha(pak),supported_executable_hashes=support,payload={n:sha((OUT/'payload'/n).read_bytes()) for n in payload})
 text(OUT/'patch-manifest.json',json.dumps(manifest,ensure_ascii=False,separators=(',',':')))
 for name in ['Install-Patch.ps1','PatchEngine.cs']:text(OUT/name,(ROOT/name).read_text(encoding='utf-8-sig'))
 (OUT/'Install-Patch.cmd').write_text('@echo off\r\npowershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Install-Patch.ps1"\r\npause\r\n',encoding='ascii')
 restore=(ROOT.parent/'Restore-Update.ps1').read_text(encoding='utf-8-sig').replace("'patch104.pak',","'patch104.pak','ReworkCharacterTemplates.dat','QuestScenes.sqa','"+WORLD_GUIDE+"',")
 restore=restore.replace("$ErrorActionPreference='Stop'", "$ErrorActionPreference='Stop'\nImport-Module (Join-Path $PSHOME 'Modules\\Microsoft.PowerShell.Utility\\Microsoft.PowerShell.Utility.psd1') -Force")
 text(OUT/'Restore-Patch.ps1',restore)
 third=OUT/'third-party';third.mkdir(exist_ok=True)
 shutil.copy2(ROOT.parent/'third-party/cnc-ddraw-LICENSE.txt',third/'cnc-ddraw-LICENSE.txt')
 text(OUT/'README.md',README)
 docs=OUT/'docs';docs.mkdir(exist_ok=True)
 for name in ['CHANGELOG.md','확장캠페인-v090-사용법.txt','보스-아군배치-수정-v091.txt','유적수호대-v0150-사용법.txt','퀘스트개편-v0160-사용법.txt']:
  body=((WORK if name in ('유적수호대-v0150-사용법.txt','퀘스트개편-v0160-사용법.txt') else ROOT.parent/'docs')/name).read_text(encoding='utf-8-sig')
  if name=='CHANGELOG.md':body=body.replace('과거 실행 파일 스냅샷은 소스 ZIP의 역사 자료이며 단독 교체용 설치 패키지가 아닙니다.','원본 실행 파일·게임 데이터·과거 실행 파일 스냅샷은 공개 배포하지 않습니다.')
  text(docs/name,body)
 shutil.copy2(WORK/WORLD_GUIDE,docs/WORLD_GUIDE)
 # Strict allowlist: do not copy previous source bundles, extracted scripts, binaries or dumps.
 public=ROOT/('public-source-'+VERSION_TAG);public.mkdir(exist_ok=True)
 shutil.copy2(OUT/'README.md',public/'README.md')
 for name in ['PatchEngine.cs','Install-Patch.ps1']:shutil.copy2(OUT/name,public/name)
 shutil.copy2(OUT/'Install-Patch.cmd',public/'Install-Patch.cmd')
 for name in OWN_CS_SOURCES:shutil.copy2(source/name,public/name)
 for name in ['Launcher.cs','WideLauncher.cs','WideLauncherQHD.cs'] :shutil.copy2(WORK/name,public/name)
 shutil.copy2(OUT/'Restore-Patch.ps1',public/'Restore-Patch.ps1')
 shutil.copytree(OUT/'docs',public/'docs',dirs_exist_ok=True)
 shutil.copytree(OUT/'third-party',public/'third-party',dirs_exist_ok=True)
 events=public/'world-events';events.mkdir(exist_ok=True)
 for name in WORLD_EVENT_SOURCES:shutil.copy2(WORK/name,events/name)
 text(events/'README.md',WORLD_SOURCE_README)
 # Build tooling is useful, but requires the developer's private, owned game inputs.
 shutil.copy2(Path(__file__),public/'build_patch_release.py')
 allowed_public={'README.md','PatchEngine.cs','Install-Patch.ps1','Install-Patch.cmd','Restore-Patch.ps1','build_patch_release.py',*OWN_CS_SOURCES,'Launcher.cs','WideLauncher.cs','WideLauncherQHD.cs','third-party/cnc-ddraw-LICENSE.txt'}
 allowed_public.update('docs/'+name for name in ['CHANGELOG.md','확장캠페인-v090-사용법.txt','보스-아군배치-수정-v091.txt','유적수호대-v0150-사용법.txt','퀘스트개편-v0160-사용법.txt',WORLD_GUIDE])
 allowed_public.update('world-events/'+name for name in [*WORLD_EVENT_SOURCES,'README.md'])
 assert {p.relative_to(public).as_posix() for p in public.rglob('*') if p.is_file()}==allowed_public,'Unexpected public source file; inspect the version output before packaging'
 assets=ROOT/('assets-'+VERSION_TAG);assets.mkdir(exist_ok=True)
 paths=[(f'SteelEmpire-Rework-v{VERSION}-PatchOnly.zip',OUT),(f'SteelEmpire-Rework-v{VERSION}-PatchSource.zip',public)]
 for name,folder in paths:
  with zipfile.ZipFile(assets/name,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for p in sorted(folder.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(folder).as_posix())
  with zipfile.ZipFile(assets/name) as z:assert z.testzip() is None
 text(assets/'SHA256SUMS.txt',''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(assets.glob('*.zip'))))
 text(ROOT/'build-report.json',json.dumps({p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in assets.iterdir()},indent=2))
 print((ROOT/'build-report.json').read_text(encoding='utf-8-sig'))

README='''# 강철제국 리워크 — 원본 보유자용 패치 v0.17.0

v0.17.0 — 연간 행사·전설 설계도
- 1·7월에는 점령 보수와 본거지 상납금, 3·9월에는 전투 경험치, 5·11월에는 배송 보수를 두 배로 받습니다.
- 유적·파견 기록으로 전설 장비 4종의 설계도를 해금해 포룸에서 제작할 수 있습니다.
- 자세한 일정과 제작 조건은 docs/연간행사·전설설계도-v0170-사용법.txt에 있습니다.

v0.16.1 — 퀘스트 삽화에 원본 이벤트 화면 배치 적용
- 기존 삽화 여섯 장의 구도를 조정했습니다. 본편 이벤트와 같은 위치에 장식 액자가 뜨고 아래에 대사가 이어집니다.

v0.16.0 — 삽화와 현장 사건
- F8 전역 의뢰 38종의 의뢰문·결과문 개편, 무전 해독·갱도 인양·악단 앙코르 3종 추가.
- 지역별 발신 도시와 목표 다양화, 미지급 보상의 다음 날 재시도.
- 퀘스트·파견·유적 대화에 상황별 삽화 6종을 표시합니다.
- 사용법은 docs/퀘스트개편-v0160-사용법.txt에서 확인할 수 있습니다.

v0.15.0 — 유적별 연간 3단계 수호대 전투

유적마다 연1회 실제 3단계 수호대 전투에 도전합니다. 보병Lv30 → 항공Lv40 → 기갑·보병Lv50이며, 3단계를 모두 이기면 연간 혜택과 보물을 받습니다. 보스형은 제외하고 유적마다 다른 편성을 사용합니다.

파견 자동 추천은 유지합니다. 임무만 고르면 실제 성공률·추가 지급률·참가 인원수·평균 레벨 순으로 편성합니다.
- 퀘스트 목표·진행·부족한 수량을 확인하고 목표 도시로 이동을 선택할 수 있습니다.
- 파견 상태·실제 예상 지급금과 준비금 차액을 확인하며, 진행 중인 같은 임무에 새 대장·남는 인원으로 추가 파견할 수 있습니다.
- 연간 유적 기본 혜택에 저장된 무작위 추가 발견을 더하고, 매우 드물게 왕실 보물과 영구 유물 효과를 얻습니다.
- 기존 340바이트 파견 추가 기록과 기존 완료·보상 기록을 유지합니다.
- 상세 조작: docs/유적수호대-v0150-사용법.txt

v0.13.0 — 해외 파견·유적 탐험
- F8 → 해외 파견·유적에서 목적지·임무를 고르면 포룸 대기 인원에서 대장까지 자동 추천 편성합니다.
- 기존 9개 군단과 별도인 파견대 4개를 운영하며 경험치·지급금·설계도·수집 유물을 얻습니다.
- 실제 유적 방문으로 해마다 한 번 혜택을 선택하고, 발견한 유적의 탐험대를 파견합니다.
- 설계도는 기존 장비의 제작을 해금합니다. 장비 능력치를 임의의 개량형으로 바꾸지 않습니다.
- 파견 기록은 손상 검사를 포함한 세이브 추가 기록으로 보관하고 저장 파일을 안전하게 교체합니다.
- v0.12.1의 병과 자격·해병교육소·방어 +15·재훈련 알림·민간군단 순회 수정도 포함합니다.
- 조작과 보상·저장 안내: docs/유적수호대-v0150-사용법.txt

v0.12.0 — 전역 이벤트 38종 단일 목표·자동 완료 개편
- 각 사건을 방문·점령·물자/아이템/장비 준비·건물 완공 중 한 가지 목표로 정리했습니다.
- 담당 군단, 필수 인물·병과, 연속 경유지와 별도 이벤트 전투 시작 조작을 요구하지 않습니다.
- 어느 아군 군단이든 자연스럽게 도착한 결과를 확인하며, 점령은 실제 아군 전투 군단의 주둔을 확인합니다.
- 목표를 달성하면 안전한 기본 화면에서 비용과 보상을 자동 정산합니다. 물품은 예비품, 장비는 포룸의 완전히 수리된 미배치 재고를 사용합니다.
- 진행 중인 기존 카드와 부분 지급된 보상·완료 기록, 본편 분기와 개인 저장은 보존합니다.
- 민간군단 자동 공연, 기존 이벤트 창과 누적 패치·에디터·기본/FHD/QHD 런처 기능을 유지합니다.
- v0.11.4의 실제 전차·항공기 분류 검사 수정과 저장 로드 중 자동 대화 차단도 포함합니다.
- 상세 조작: docs/유적수호대-v0150-사용법.txt

다음 v0.11.0 항목은 최초 도입 당시의 변경 이력입니다.

v0.11.0 — 종전 이후 전역 이벤트 36종
- 최후의결전 실제 승리 후에도 이어지는 6분류 36종의 사건을 추가합니다.
  도시 생활·내정, 이동·배송, 군단 생활, 탐험·수집, 선택 전투, 연속 후일담으로 구성됩니다.
- 도시·월드 기본 화면에서 F8 → ‘종전 이후 전역 이벤트 36종’을 선택합니다.
  미발견 사건을 포함한 전체 목록·발동 조건을 엔딩 전에도 열람할 수 있습니다.
- 새 소식은 게임 시간 7~10일 간격으로 제안하며 동시에 최대 3개를 보관합니다.
  전투를 포함한 소식은 활성 1개, 새로운 전투 계약은 게임의 한 달에 1개로 제한합니다.
  조건을 만족하는 도시가 없으면 생성을 미루며 반복 팝업으로 플레이를 중단하지 않습니다.
- 수송은 실제 군단 이동·도착을 확인합니다. 수락 후 60일은 권장 목표이며
  넘겨도 자동 실패·벌금·시설 파괴가 없습니다. 담당 군단 변경과 자동 이동 재시도를 지원합니다.
- 예비 물품만 납품하며 장착품은 자동 해제하지 않습니다. 고용 인원과 장비는
  포룸 대기 명단·정비창에, 일반 물품은 담당 군단의 가방에 인계합니다.
  보관함·인원·자원 한도에 걸린 보상은 대기로 유지하고 이미 정산한 부분을 다시 주지 않습니다.
- 블랙파워 재건은 적 본거지 점령을 요구하지 않고 인근의 안전한 연락도시를 방문합니다.
  카란토 재건, 엑제로스 후일담, 여섯 나라 기록 수집, 자유 순서 지원 병과 작업,
  서로 다른 사건 12·24·35종 완료에 따른 종전 기념제를 포함합니다.
- 기존 본편 분기·병과 기술·보스 해금·본거지 점거·사망 규칙을 초기화하지 않습니다.
  전투는 기존 손실·경험치 규칙을 사용합니다. 비용이 있는 수락과 보상 수령 상태는 저장에 기록합니다.
- 자세한 조작과 36종 선택지는 docs/종전후-전역이벤트-v0110-사용법.txt를 참조하세요.
  위 내용은 도입 당시의 진행 방식입니다. 최신 진행 방법은 v0.12.0 단일 목표 사용법을 확인하세요.

다음은 이전 누적 버전의 변경 이력입니다.

v0.10.1.1 수정 사항
- 라이벌 승리 후 저장을 불러왔을 때 블랙파워의 기존 지휘자와 인물 명단이 없어
  복귀가 중단되는 문제를 수정했습니다. 이 경우 일반 블랙파워 사병을 임시 지휘자로
  등록하여 AI와 일반 병력 재편을 복구합니다. 죽은 이야기 인물은 부활시키지 않습니다.
- 복귀는 별도 날짜를 기다리지 않고 이벤트 대화 종료 후 도시/월드 화면에서 처리합니다.
  본거지에 아군·다른 세력이 주둔한 경우에는 철수 후 처리합니다.
- 제보 저장의 빈 지휘자 명단을 재현하고 실제 게임 저장 코드가 임시 지휘자와
  해당 인물 기록을 함께 저장하는지 검증했습니다.

v0.10.1 변경 사항
- 라이벌 이벤트를 실제 승리로 완료하면 블랙파워 용병단의 일반 활동을 복구합니다.
  생존 부대가 없으면 일반 보병 80명으로 한 번 재편하며, 이후에는 원래 재모집 AI를 따릅니다.
  본거지가 아군·다른 세력에 점령 중이면 철수할 때까지 복귀를 미룹니다.
  이야기 보스·보상·죽은 인물을 되살리거나 이벤트를 다시 실행하지 않습니다.
- 최후의결전 승리 후 엑제로스의 벨키카·베른·시노페·에볼라쿰이 새 배송 의뢰의
  목적지 후보에 포함됩니다. 원래 목적지 역할 필터와 수송료·수락·보상·이동 규칙은 유지합니다.
  기존에 생성된 의뢰의 목적지는 바뀌지 않으며 새 의뢰 생성부터 적용됩니다.
  전투·점령을 무조건 허용하거나 최종전의 진입 조건을 해제하는 변경은 아닙니다.
- v0.10.1 당시에는 숨겨진 후일담이 별도 기획안 단계였습니다. 신규 전역 전투·보상은 v0.11.0에서 추가합니다.

v0.10.0 누적 변경 사항
- 인물 에디터에서 13개 병과를 변경할 수 있습니다. 운전병 전환을 지원하며,
  부대·보직·훈련 배치는 먼저 해제해야 합니다. 이름·레벨·능력치는 유지합니다.
- 장비 에디터를 추가했습니다. 차량·항공기 24종, 차체 33종, 포탑 55종의 기준
  성능과 저장 파일에 이미 보유한 아군·적군 장비를 수정할 수 있습니다.
  기준 성능 변경은 이후 생성 장비에 적용됩니다. 업데이트 후 변경 재적용 기능을 제공합니다.
- 막사 훈련의 원래 건물 기술 조건을 복구했습니다. 중장갑보병은 정부청사 완공 후
  신규 훈련됩니다. 기존 장갑보병 재훈련 기능은 유지합니다.
- 에투루리아 일반 도시 전체를 적성지역으로 만들던 설정을 해제하고 카란토 수도만
  점령 대상으로 제한했습니다. 카란토에는 최대 80명 수비대를 한 번 생성합니다.
  용병단 본거지는 해당 용병단이 점령한 일반 도시가 없을 때 공격할 수 있습니다.
  v0.9.9의 일반 도시 방어군은 식별 가능한 기본 편성만 정리하며 실제 점령군은 보존합니다.
- 군단 인원 상한을 보병 33명, 기계화 19명으로 조정했습니다. 지휘 인원도 포함합니다.
- 팬저파우스트 3종의 기량/명중 보정을 각각 30/26으로, 대공 공격을 각 무기의
  대벽 공격과 같은 60/65/90으로 높였습니다. 사거리와 다른 수치는 유지합니다.
- 유격훈련장은 병기창 LEVEL 1, 중화기사격장은 시청을 요구하도록 건설 조건을 교환했습니다.
- 적 군단장 사망 후 잔여 적의 사기를 0으로 만들고 사기 붕괴 상태를 적용합니다.
  기존 3턴 후 잔여 병력 전멸 처리도 유지합니다.
- 주둔 중인 일반 지원 병과가 새 작업 기간을 1명당 2%, 최대 10% 줄입니다.
  건축가는 건설, 과학자는 연구, 기술자는 장비 생산에 적용되며 기존 소장 보정과 병행합니다.
- 차량·보병 혼합 기계화군단을 배송 자동 출발에서 제외하던 검사를 수정했습니다.
- SteelReworkLauncher.exe를 추가했습니다. 실행 시 GitHub 최신 정식 패치를 확인하고
  새 버전이 있으면 다운로드·SHA256 검증·백업 설치 후 재시작합니다. 기본/FHD/QHD 실행을 지원합니다.

실제 게임의 훈련·생산·보상·출격·도시 배치·공연 정산 코드를 에뮬레이션해 검증했습니다.
그래픽·입력·대화·일부 할당에 경계 대체를 사용하는 에뮬레이션 검증입니다.

v0.9.8.2는 배송 의뢰 자동 이동에서 출격 가능한 군단이 하나일 때 별도 군단 선택 없이
출발하도록 개선합니다. '목적지로 자동 이동'을 선택하면 유일한 군단을 자동 선택하며,
여러 군단이 출격 가능하면 기존 선택창을 유지합니다. 출발 도시는 저장된 도시 번호로
다시 찾아 도시/월드 화면 전환으로 대기 명령을 잃지 않도록 보완했습니다.
보병·전차·항공의 제1~9군단, 도시/월드/다른 도시 화면과 취소·다중 선택 등을
새 검사 89건과 기존 의뢰 검사 112건으로 확인했습니다. 실제 출격·월드 등록·목적지
지정 코드를 에뮬레이션했으며 그래픽 생성과 화면 전환 등은 대체 경계입니다.
다음 배송 의뢰 수락부터 적용되며 이미 수락한 의뢰의 이동 선택창을 소급 표시하지 않습니다.

v0.9.8.1은 수정된 인물 에디터 v0.9.8.1을 포함한 누적 패치입니다.
일부 약 94KB 저장 파일이 열리지 않던 문제를 수정했습니다. 파일 첫 값을 고정된
식별자로 오인하던 검사를 바로잡았으며, 실제 95,676바이트 제보 파일의 인물 20명
읽기·수정·저장·재열기·백업 복원을 확인했습니다. 크기와 첫 값 조합 및 실제 저장
복사본으로 1,351개 검사를 통과했습니다. 합성 파일은 에디터 파서 검사 전용입니다.
도시·인물 목록 구조 검증과 백업 기능을 유지합니다. 이 에디터 수정도 포함됩니다.

## 다운로드

[최신 릴리스](https://github.com/pol2002co-cloud/steel-empire-rework/releases/latest)에서
SteelEmpire-Rework-v0.12.0-PatchOnly.zip을 받으세요. 신규 설치와 기존 리워크 업데이트에
사용하는 누적 패치이며 원본 게임이 필요합니다. 기존 리워크 사용자도
전역 이벤트와 누적 수정을 적용하려면 이 누적 패치를 설치하세요. 수정된 에디터도 포함됩니다.
PatchSource.zip은 설치 도구·런처·에디터·자체 전역 이벤트 소스이며 게임 실행용 패키지가 아닙니다.

## 기존 누적 기능

v0.9.8은 아군 INF MK1·INF MK2·블랙드래곤·랜드배틀쉽·포트레스에
적 진영(좌상단)을 향하는 새 본체와 개별 무기 그림을 적용합니다.
사용자가 승인한 반대 시점 시안에 따른 새 그림이며 원본과 외형 차이가 있습니다.
포탑을 포함한 54개 개별 부품의 표시 위치·포구 위치·투명 픽셀 클릭 판정을 맞췄습니다.
파괴된 무기는 개별 표시와 판정에서 제거되며 적 보스 그림은 원본을 유지합니다.
원본의 애니메이션 길이·프레임별 발사/효과 이벤트는 실행 중 원본 자원에서 가져와
보존합니다. 새 본체와 무기 그림은 정지 그림을 사용하므로 원본의 세부 프레임별
모양 변화까지 새로 그린 버전은 아닙니다. 기존 비행 부유 동작과 전투 규칙은 유지합니다.
전투 종료·상태 갱신 시 새 그래픽 자원의 메모리를 해제합니다.
새로 시작하거나 저장을 불러온 전투부터 적용됩니다.

v0.9.7은 배송 자동 이동에서 보병 군단을 전차 좌석 검사로 잘못 제외하던 문제를 수정합니다.
한 군단만 주둔한 경우에도 제1~9군단 번호와 병종에 맞게 목록에 표시합니다.
보병·항공은 각 원래 출격 규칙을 따르고, 전차 군단의 탑승 좌석 검사는 유지합니다.

v0.9.6은 점령된 일반 도시를 공격할 때 해당 도시 탈환 의뢰를 자동 수락합니다.
의뢰 주도시를 먼저 방문하지 않아도 기존 공격 확인 뒤 전투를 진행할 수 있습니다.
완료 후 보상은 기존 의뢰 주도시에서 받습니다. 이미 보상 대기 중인 의뢰는
완료 상태를 유지하며 재공격을 허용하고, 보상을 중복 생성하지 않습니다.
적 본거지의 '점령 도시가 없어야 공격 가능' 조건과 이야기 전용 진입 제한은 유지합니다.

물품 배송 의뢰를 수락하면 '목적지로 자동 이동 / 직접 이동'을 선택할 수 있습니다.
자동 이동을 선택한 다음 그 도시에 주둔한 출격 가능 군단을 선택하세요.
제1~9군단을 목록으로 표시하며 많은 경우 '다음 군단 목록'으로 넘깁니다.
선택한 군단이 월드맵으로 출격하여 목적지에 우클릭한 것과 같은 이동 명령을 받습니다.
이동 시간·경로·도중 전투·현지 인도·보상 수령은 기존 규칙을 따릅니다.
취소하거나 출격 가능한 군단이 없으면 의뢰만 수락하고 도시에 남습니다.
이미 수락한 배송은 다시 수락하지 않으므로 이 선택창이 소급 표시되지는 않습니다.

v0.9.5는 아군 이벤트 보스 5종 탑승자의 전투 경험치 누락을 수정했습니다.
일반 전차·항공기와 같은 경험치·레벨업을 적용하고 99레벨 탑승자의 경험치도
다른 생존 인물에게 재분배합니다. 기존 경험치 200 제한 제거도 유지합니다.

v0.9.4는 이벤트 보스의 무료 재배치와 아군 보스의 전투 방향을 수정했습니다.
포룸에 군단장 1명만 남긴 호환 군단을 주둔시킨 뒤 F9에서 같은 병기를 선택하세요.
보관 중인 같은 병기가 있으면 무료 재배치 확인이 표시됩니다. 재배치는 보관 중인
실제 병기의 HP와 상태를 유지합니다. 블랙드래곤은 파일럿·항공 군단, 나머지는
드라이버·장갑 군단이 필요합니다. HP가 0인 병기는 먼저 정비하세요.
아군 보스 5종의 본체·부품·선택 테두리를 좌우 반전하고 클릭 판정도 맞췄습니다.
적 보스의 방향과 기존 전투 배치는 유지합니다.

v0.9.3의 블랙크로우 잔존 야전 부대 반격과 빈 본거지 재탈환도 포함합니다.
최대 6일 간격으로 대기 중인 야전 부대가 가까운 아군 점령 일반 도시를 공격합니다.
철수해 비워진 점거 본거지가 있으면 우선 되찾습니다. 본거지 주둔 중 적 충원 중단,
기존 이동 명령, 전투와 월별 상납금 규칙은 유지합니다.
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
생성합니다. 생성 결과는 검증된 v0.17.0 실행 파일 및 데이터 팩과 바이트 단위로 동일합니다.
인물 에디터용 기준 데이터도 사용자 PC에서 생성하며 에디터에는 내장하지 않습니다.
ReworkCharacterTemplates.dat는 에디터 옆에 유지하고 재배포하지 마세요.

원본은 ReworkBackups에 백업합니다. 기존 저장과 ddraw.ini 설정은 유지합니다.
설치 직전 저장은 같은 백업 폴더의 Saves에도 별도로 보관합니다. 저장 복원은 수동입니다.
설치 후 SteelReworkLauncher.exe를 실행하면 최신 패치 자동 확인과 실행 모드를 이용할 수 있습니다.
이전 SteelRework.exe 또는 SteelReworkQHD.exe도 사용할 수 있습니다.
게임 폴더 전체나 설치 후 생성된 게임 파일을 다른 사람에게 보내지 말고, 원본이
없는 PatchOnly ZIP 또는 최신 릴리스 링크를 공유하세요.

## 복원

게임·런처·에디터 종료 후 새로 생성된 ReworkBackups/v0.17.0-delta-날짜 폴더의
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

PatchSource는 원본 데이터 없는 설치 엔진·런처·에디터의 C# 코드와 신규 전역 이벤트의 자체 작성 Python/C 코드·검사입니다.
인물 에디터를 빌드할 때 원본 char.dat를 리소스로 넣지 마세요.
배포 변경분은 patch-manifest.json에 있으며, 기계어 함수·데이터 변경을 포함합니다.
원본 게임 C/C++ 소스와 게임 데이터는 제공하지 않습니다.
'''
WORLD_SOURCE_README='''# 신규 전역 이벤트 자체 작성 소스

world_event_simple_catalog.py는 38종의 단일 목표·자동 완료 사건 데이터입니다.
world_event_catalog.py는 기존 진행 카드·보상의 호환성 유지를 위한 이전 사건 데이터입니다.
world_event_state.py는 저장 상태, world_event_actions.py는 원본 함수 연결,
world_event_native.c는 사건 UI·목표 진행, world_events_patch.py는 CP949 표와 고정 주소 코드 생성을 담당합니다.
world_tour_actions.py는 일반 댄서·영웅 댄서의 자체 자동 공연 정산 연결을 담당합니다.
expedition_native.c와 expedition_catalog.py는 별도 파견대·유적·제작의 UI와 규칙을 담당합니다.
expedition_actions.py는 원본 인원 편성·경험치·귀환 처리와 연결하고,
expedition_storage.py/expedition_storage.h는 원본 저장 함수와 손상 검사·안전한 추가 기록을 연결합니다.
ruin_visits.py는 네 실제 유적의 원본 스크립트 진입을 관찰하며 기존 이야기 처리를 유지합니다.
world_event_compile.py는 개발 워크스페이스의 검증된 프로젝트 로컬 Zig를 사용합니다.

원본 실행 파일·게임 데이터·기준 인물 표·저장·메모리 덤프·개인 검증 자료·컴파일러는 포함하지 않습니다.
이 폴더만으로 게임을 실행하거나 전체 리워크를 재빌드할 수 없습니다.
실행 파일 연결과 통합 검사는 개발자의 원본 보유 워크스페이스와 이전 누적 패치 모듈이 필요합니다.
검사 파일은 구현 검토용으로 포함하며 실제 게임 장기 플레이 검증을 대신하지 않습니다.
test_world_event_simple_catalog.py와 test_world_event_simple.py는 새 목표와 상태 이행을 검사합니다.
test_goal_occupation.py는 원본 도시 진입·철수 함수와 군사 점령 판정을 검사합니다.
test_ruin_guardians.py는 연간 3단계 진행·승패·저장·보상 중복 방지를 검사합니다.
test_ruin_guardian_actions.py는 12개 편성의 원본 전투 생성·배치·장비·정리 경로를 검사합니다.
test_expedition_auto.py는 실제 성공률·추가 지급률 기준의 자동 편성을 전수 조합과 비교합니다.
test_quest_usability.py, test_expedition_usability.py, test_ruin_random.py는 목표 안내·반복 파견·연간 추첨을 검사합니다.
'''
if __name__=='__main__':build()
