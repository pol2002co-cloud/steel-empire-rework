from pathlib import Path
import hashlib,json,shutil,zipfile,struct
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parent/'steel-rework'
GAME=Path('D:/Games/DGGL/Games/EoSteel_Win')
ASSETS=ROOT/'assets'
VERSION='0.8.2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def text(p,t):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8-sig')
def archive(name,files,base=''):
 with zipfile.ZipFile(ASSETS/name,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for dest,p in sorted(files.items()):z.write(p,base+dest)
 with zipfile.ZipFile(ASSETS/name) as z:
  assert z.testzip() is None
  assert not any(x.lower().endswith(('.sav','.dmp','.log')) or 'backups/' in x.lower() for x in z.namelist())
def build():
 ASSETS.mkdir(exist_ok=True)
 m=json.loads((WORK/'manifest.json').read_text(encoding='utf-8'))
 assert m['version']=='0.8.2-experimental' and sha(WORK/'package/SteelEmpire.exe')==m['output_sha256']
 assert sha(GAME/'SteelEmpire.exe')==m['output_sha256']
 names=['SteelEmpire.exe','SteelRework.exe','SteelRework169.exe','SteelReworkQHD.exe','SteelCharacterEditor.exe','patch104.pak','ddraw.dll','ddraw.ini','SteelCharacterEditor-사용법.txt','SteelRework169-사용법.txt']
 payload={n:WORK/'package'/n for n in names}
 supported=[m['source_sha256'],m['output_sha256']]+[sha(p) for p in WORK.glob('SteelEmpire-v*.exe')]
 release=dict(version=VERSION,supported_executable_hashes=sorted(set(supported)),payload={n:sha(p) for n,p in payload.items()})
 text(ROOT/'release-manifest.json',json.dumps(release,ensure_ascii=False,indent=2))
 text(ROOT/'docs/CHANGELOG.md','''# v0.8.2 누적 배포 기록

## v0.8.2
원본 의뢰 삭제 함수가 종류와 목적지가 같은 다른 의뢰를 지우는 문제를 수정했습니다. 보상을 지급한 의뢰 자체를 삭제합니다. 특정 개인 저장의 보석지팡이 복구는 일반 배포에서 실행하지 않습니다.

## v0.8.1
F8 사건 상세의 발동 조건과 강제 설정에서 조건 무시 예약을 켜고 끌 수 있습니다. 주요 사건 9개의 최초 발동 조건을 우회합니다. 미시작 값 0인 사건만 가능하며 시작·거절·완료 기록은 초기화하지 않습니다. 다른 사건 진행 중에는 대기하고, 발동하면 예약을 해제합니다. 후속 전투·퍼즐·전달은 직접 진행합니다.

## v0.8.0
월드맵·도시 기본 화면 F8 이벤트 진행창. 주요 사건 9개, 관련 기록 16개, 현재 단계, 모든 발동 조건, 선택 분기를 공개합니다.

## v0.7.4
술집 용병의 포커 자금을 0으로 설정하고 고용 동의 절차를 통해 바로 고용합니다.

## v0.7.3
전투에서 이미 99레벨인 생존자의 경험치를 99 미만 생존자에게 균등 재분배합니다. 사망자와 98→99 상승 시 초과 경험치는 별도 재분배 대상이 아닙니다.

## v0.7.2
브라보니케 입력 시 남은 적을 제거하고 즉시 원래 승리 정산으로 이동합니다.

## v0.7.1
여섯 번째 재훈련 항목을 처리할 UI 배열과 메모리 크기를 확장하여 재훈련소 진입 오류를 수정했습니다.

## v0.7.0
새로 생성되는 적 용병단은 기존 병종·장비 특성을 유지하며 보병 80명(군단장 포함), 혼성 기갑 7대+보병 18명, 항공기 9대 구성으로 확장합니다. 이미 저장된 적 부대와 고정 스크립트 부대는 일괄 보충하지 않습니다.

## v0.6.2
개인 전투 경험치 200 상한을 제거했습니다. 기존 계산과 최소 5는 유지합니다.

## v0.6.1
미니맵 도시명을 마우스 호버 시 표시하는 방식으로 복원했습니다. 상시 도시명 표시는 최종 동작이 아닙니다.

## v0.6.0
레벨 15 이상 장갑보병→중장갑보병 재훈련(방어+20, 철25·석유15·금5000·20일). 공항 없는 도시의 항공 부대는 A 키로 공항 화면을 열어 출격. 메달 7종 판매. 에디터에서 군단 공격/방어 보정, 지휘/특수능력, 저장에 존재하는 포룸 밖 인물을 편집합니다.

## v0.5.0
미니맵 도시 위치에 마우스를 올리면 이름을 표시합니다.

## v0.4.0
적 군단장 사망 후 3턴 기한에 남은 적을 자동 제거합니다. 그 전에 전멸시키면 즉시 정산합니다.

## v0.3.0
이름 있는 영입 동료는 전투 사망 후 다음 자정에 최대 HP로 복귀합니다. 일반 용병은 기존 처리. 항공 부대의 모든 도시 착륙을 허용합니다.

## v0.2.0 및 도구 배포
일반 병종 13종 훈련, 일반 전차·항공기 구매 확장, 훈련대장 레벨 비례 훈련 레벨(최대30), 포커 정산 시 플레이어 승리. 인물 에디터의 능력치·상태 편집. cnc-ddraw v7.1.0.0 호환 계층과 기본·16:9·2560×1440 QHD 런처.

상세 비용·병종·검증·원복 이력은 함께 제공하는 원래 누적 패치 노트와 개별 사용법을 참고하세요. 과거 실행 파일 스냅샷은 소스 ZIP의 역사 자료이며 단독 교체용 설치 패키지가 아닙니다.
''')
 docnames=['강철제국_리워크_최종_패치노트_v0.8.0.txt','이벤트-강제진행-v081-사용법.txt','의뢰-완료-수정-v082.txt','이벤트-진행창-사용법.md','적용병단-편성표.md']
 for n in docnames:shutil.copy2(WORK/n,ROOT/'docs'/n)
 text(ROOT/'docs/DISTRIBUTION.md','''# 배포 구성과 제작

전체 게임: 원본 게임의 .pak 데이터, Movie 영상, Mss 오디오 구성요소, 리워크 실행 파일·데이터 팩·런처·에디터·기본 화면 설정을 포함합니다. 별도 DOS 실행기나 개인 저장, 백업, 로그는 포함하지 않습니다.

Update: 지원 실행 파일 해시를 확인한 후 현재 누적 패치를 설치합니다. 기존 화면 설정과 모든 저장을 유지하며 프로그램 파일을 백업합니다.

Tools: 게임 폴더에 풀어 사용하는 런처 3종과 에디터입니다. 전체 게임에 이미 포함되어 있습니다.

Source: steel-rework의 패치 모듈·검증 코드·C# 런처 및 에디터 코드·제작용 데이터와 역사 실행 파일 스냅샷, 배포 스크립트를 포함합니다. 원본 게임 자체의 C/C++ 소스 코드는 포함되어 있지 않습니다.

제작에는 Python 3와 pefile, keystone-engine, capstone, unicorn이 필요합니다. archive.py의 SRC를 게임 설치 경로로 지정하세요. build.py는 검증된 원본 해시의 실행 파일이 설치 폴더나 ReworkBackups 안에 있어야 빌드합니다. 해당 원본은 전체 게임 ZIP의 development/SteelEmpire-original.exe로 제공됩니다. 이를 별도의 제작용 설치 사본의 ReworkBackups/original/SteelEmpire.exe로 복사할 수 있습니다.

C# 소스는 Windows .NET Framework csc.exe로 빌드합니다. 에디터는 char.dat를 리소스로 포함해야 합니다. 실제 게임 전체 분기 완주 검증은 별도입니다.

구버전 개별 설치 스크립트와 개인 저장 복구 스크립트는 공개 설치 프로그램으로 사용하지 않습니다. 최신 업데이트에는 경로를 지정할 수 있는 Install-Update.ps1을 사용하세요.
''')
 third={'third-party/'+p.name:p for p in (ROOT/'third-party').iterdir() if p.is_file()}
 docs={'docs/'+p.name:p for p in (ROOT/'docs').iterdir() if p.is_file()}
 common={**docs,**third,'README-Rework.md':ROOT/'README.md'}
 update={**common,**{'payload/'+n:p for n,p in payload.items()},'Install-Update.ps1':ROOT/'Install-Update.ps1','Restore-Update.ps1':ROOT/'Restore-Update.ps1','release-manifest.json':ROOT/'release-manifest.json'}
 archive(f'SteelEmpire-Rework-v{VERSION}-Update.zip',update)
 tools={**common,**{n:p for n,p in payload.items() if n.startswith(('SteelRework','SteelCharacter'))}}
 archive(f'SteelEmpire-Rework-v{VERSION}-Tools.zip',tools)
 full={**common,**payload}
 for p in GAME.iterdir():
  if p.is_file() and (p.suffix.lower()=='.pak' or p.name in ['Mss32.dll','README.txt']):full.setdefault(p.name,p)
 for sub in ['Movie','Mss']:
  for p in (GAME/sub).rglob('*'):
   if p.is_file():full[p.relative_to(GAME).as_posix()]=p
 # A verified original permits rebuilding from this authorized full package.
 originals=sorted((GAME/'ReworkBackups').glob('*/SteelEmpire.exe'))
 original=next(p for p in originals if sha(p)==m['source_sha256'])
 full['development/SteelEmpire-original.exe']=original
 archive(f'SteelEmpire-Rework-v{VERSION}-FullGame.zip',full,'SteelEmpire-Rework/')
 source={**common,'README.md':ROOT/'README.md'}
 excluded={'prepare_quest_save_repair.py','read_crash.py','crash_probe.py'}
 for pattern in ['*.py','*.cs','manifest*.json']:
  for p in WORK.glob(pattern):
   if p.name not in excluded:source['steel-rework/'+p.name]=p
 for p in (WORK/'editor').glob('*.cs'):source['steel-rework/editor/'+p.name]=p
 for sub in ['extracted','event-analysis']:
  for p in (WORK/sub).rglob('*'):
   if p.is_file():source['steel-rework/'+p.relative_to(WORK).as_posix()]=p
 for p in WORK.glob('SteelEmpire-v*.exe'):source['steel-rework/'+p.name]=p
 for p in (ROOT/'third-party').iterdir():source['third-party/'+p.name]=p
 for p in (ROOT.parent/'vendor/cnc-ddraw-v7.1.0.0').glob('ddraw.*'):source['vendor/cnc-ddraw-v7.1.0.0/'+p.name]=p
 for p in ROOT.glob('*.ps1'):source['distribution/'+p.name]=p
 source['distribution/build_release.py']=Path(__file__)
 archive(f'SteelEmpire-Rework-v{VERSION}-Source.zip',source)
 checks=''.join(sha(p)+'  '+p.name+'\n' for p in sorted(ASSETS.glob('*.zip')))
 text(ASSETS/'SHA256SUMS.txt',checks)
 report={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in ASSETS.glob('*.zip')}
 text(ROOT/'release-files.json',json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
if __name__=='__main__':build()
