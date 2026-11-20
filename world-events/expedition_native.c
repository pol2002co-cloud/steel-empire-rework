/* Separate native rosters; only bounded, pointer-free metadata enters the footer. */
typedef struct {const char *name,*text;u32 days,cost,gold,xp,job;} EXMission;
typedef struct {const char *name;u32 machine,gold,iron,oil,days,factory;} EXRecipe;
typedef struct {const char *condition,*unit,*stats;u32 required;} EXLegend;
typedef struct {const char *name;u32 town;} EXRuin;
typedef struct {const char *name,*summary;u32 profile,level,infantry,machines;} EXGuardian;
#include "expedition_catalog_generated.h"
#include "ruin_guardians_generated.h"
#include "expedition_storage.h"
#define EXP_KEY "SteelEmpireRework.Expeditions.0130"
#define EXP_MAGIC 0x45585331u
typedef struct {u32 status,mission,ruin,depart,due,chance,bonus,outcome,seed,paid,extra_gold,retry;} EXRun;
typedef struct {u32 visited,used,seen,home,legion,story,successes;} EXVisit;
typedef struct {u32 magic,version,rng,blueprints,artifacts,completed;EXRun runs[4];EXVisit ruins[4];u32 recipe,due,order_retry;} EXSave;
typedef struct {EXSave save;u32 world,warning,contact_army,contact_x,contact_y;} EXRuntime;
static EXRuntime *exp_get(int create){NoticeApi api;EXRuntime *r;u32 h=MAIN_HWND;if(!h||!world()||!notice_api(&api))return 0;r=(EXRuntime *)api.get(h,PTR(EXP_KEY));if(!r&&create){r=(EXRuntime *)((Allocate)0x450452)(sizeof(*r));if(!r)return 0;memset(r,0,sizeof(*r));if(!api.set(h,PTR(EXP_KEY),PTR(r))){((Release)0x4500e6)(PTR(r));return 0;}}if(r&&(r->world!=world()||r->save.magic!=EXP_MAGIC)){memset(r,0,sizeof(*r));r->world=world();r->save.magic=EXP_MAGIC;r->save.version=1;r->save.rng=0x51e7a931u^now();}return r;}
static u32 exp_random(EXSave *s){u32 n=s->rng;if(!n)n=0x51e7a931u;n^=n<<13;n^=n>>17;n^=n<<5;s->rng=n;return n;}
static u32 exp_year(void){return now()/360+1;}
#define EX_SEEN_YEAR 0xfffffu
#define EX_GUARD_SHIFT 16
static u32 exp_guard_state(const EXVisit *v){return (v->home>>EX_GUARD_SHIFT)&7;}
static void exp_guard_set(EXVisit *v,u32 state){v->home=(v->home&65535u)|(state<<EX_GUARD_SHIFT);}
static u32 exp_ruin_tier(EXSave *s,EXVisit *v){u32 encoded=v->seen>>20,roll,tier;if(encoded)return encoded-1;tier=0;if(v->used<v->visited){roll=exp_random(s)%10000;tier=roll<7000?0:roll<9000?1:roll<9850?2:roll<9990?3:4;}v->seen=(v->seen&EX_SEEN_YEAR)|((tier+1)<<20);return tier;}
typedef struct {u32 gold,iron,oil,artifact;const char *name,*story;} EXAnnualBonus;
static EXAnnualBonus exp_ruin_bonus(EXSave *s,u32 tier){EXAnnualBonus b;memset(&b,0,sizeof(b));b.name="고요한 유적";b.story="선택한 기본 혜택을 받았습니다.";if(tier==1){b.gold=30000;b.iron=30;b.oil=20;b.name="숨은 저장고";b.story="갈라진 벽 뒤에서 오래된 보급 저장고를 발견했습니다.";}else if(tier==2){b.gold=100000;b.iron=70;b.oil=40;b.name="잊힌 보물";b.story="잠들어 있던 보물 상자와 귀중한 자원 더미를 발견했습니다.";}else if(tier==3){b.name="별빛 제단";if(!(s->artifacts&4)){b.artifact=4;b.story="별의 나침반을 얻었습니다. 모든 파견의 성공률이 5%포인트 높아집니다. 성공률 상한은 95%입니다.";}else if(!(s->artifacts&8)){b.artifact=8;b.story="시간의 결정을 얻었습니다. 앞으로 출발하는 파견의 기간이 20% 짧아집니다. 이미 출발한 임무의 일정은 유지됩니다.";}else if(!(s->artifacts&16)){b.artifact=16;b.story="현자의 서를 얻었습니다. 파견 귀환 시 받는 경험치가 25% 늘어납니다.";}else{b.gold=150000;b.story="이미 모든 별빛 유물을 보유하고 있어 제단이 금 150,000을 선물했습니다.";}}else if(tier==4){b.gold=1000000;b.iron=200;b.oil=100;b.name="왕실의 보물고";b.story="아주 드물게 열리는 고대 왕실의 보물고를 발견했습니다. 막대한 재물과 전략 물자를 회수했습니다.";}return b;}
static int exp_valid(const EXSave *s){int i,active=0;if(s->magic!=EXP_MAGIC||s->version!=1||s->blueprints>=(1u<<EX_RECIPE_COUNT)||s->artifacts>31||s->recipe>EX_RECIPE_COUNT)return 0;for(i=0;i<4;i++){const EXRun *r=&s->runs[i];if(s->ruins[i].home>0x7ffffu||(s->ruins[i].home&65535u)>100)return 0;if(exp_guard_state(&s->ruins[i])>=5&&++active>1)return 0;if(r->status>4||r->mission>=7||r->ruin>=4||r->chance>95||r->bonus>50||r->outcome>3||r->paid>7||r->extra_gold>50000)return 0;if(r->status&&(r->due-r->depart>120||r->depart>0x0aaaaaaau||(r->status!=4&&!r->outcome)))return 0;if(s->ruins[i].story>2||s->ruins[i].successes>3||s->ruins[i].visited>497103u||s->ruins[i].used>497103u||(s->ruins[i].seen&EX_SEEN_YEAR)>497103u||(s->ruins[i].seen>>20)>5)return 0;}return 1;}
static int exp_credit(u32 gold,u32 iron,u32 oil){u32 amounts[3];int i;amounts[0]=gold;amounts[1]=iron;amounts[2]=oil;for(i=0;i<3;i++)if(V(resource(i))>2000000000u||amounts[i]>2000000000u-V(resource(i)))return 0;for(i=0;i<3;i++)V(resource(i))+=amounts[i];return 1;}
static int exp_free(u32 t,u32 p){return p&&p!=V(t+0xa0)&&V(p)!=14&&alive(p)&&!V(p+0x10)&&!V(p+0x14)&&V(p+0x38)>=1&&V(p+0x38)<=13&&V(p+0x48)>=1&&V(p+0x48)<=99;}
static int exp_contains(u32 *list,int n,u32 p){int i;for(i=0;i<n;i++)if(list[i]==p)return 1;return 0;}
static u32 exp_days(EXSave *s,const EXMission *m){return (s->artifacts&8)?(m->days*4+4)/5:m->days;}
static u32 exp_base(EXSave *s,const EXMission *m,u32 chief){u32 skill=V(chief+0x70);if(skill>200)skill=200;return 45+V(chief+0x48)/5+skill/10+((m>=&EX_MISSIONS[4]&&(s->artifacts&1))?5:0)+((s->artifacts&4)?5:0);}
static u32 exp_bonus(EXSave *s,u32 chief){u32 skill=V(chief+0x70),bonus;if(skill>200)skill=200;bonus=V(chief+0x48)/5+skill/4+((s->artifacts&2)?10:0);return bonus>50?50:bonus;}
static u32 exp_rate(u32 base,u32 sum,int n,int generic,int specialists){u32 chance=base+sum/n/10+generic/4+(specialists>5?5:specialists)*2;return chance>95?95:chance;}
static u32 exp_chance(EXSave *s,const EXMission *m,u32 *list,int n){int i,specialists=0,generic=0;u32 sum=0;for(i=0;i<n;i++){sum+=V(list[i]+0x48);generic+=V(list[i]+8)==1;specialists+=m->job&&V(list[i]+0x38)==m->job;}return exp_rate(exp_base(s,m,list[0]),sum,n,generic,specialists);}
static void exp_top(u32 p,u32 *list,int *count,int limit){int i;if(exp_contains(list,*count,p))return;i=*count;if(i==limit){if(V(p+0x48)<=V(list[i-1]+0x48))return;i--;}else (*count)++;while(i>0&&V(p+0x48)>V(list[i-1]+0x48)){list[i]=list[i-1];i--;}list[i]=p;}
static int exp_party(EXSave *s,u32 chief,const EXMission *m,u32 *list){
 u32 t=town(1),heroes[128],generics[2][20],gs[2][21],best_chance=0,best_bonus=0,best_sum=0,h,node;
 int hn=0,gc[2]={0,0},guard=0,i,j,k,c,h0,h1,g0,g1,best_n=0;
 if(!t||(chief&&(!exp_free(t,chief)||V(chief+8)!=3)))return 0;
 h=V(t+0x50a4c);node=h?V(h):0;
 while(node&&node!=h&&guard++<10000&&hn<128){u32 p=V(node+8);if(exp_free(t,p)&&V(p+8)==3&&!exp_contains(heroes,hn,p))heroes[hn++]=p;node=V(node);}
 if(chief&&!exp_contains(heroes,hn,chief))return 0;
 h=V(t+0x50a58);node=h?V(h):0;guard=0;
 while(node&&node!=h&&guard++<10000){u32 p=V(node+8);if(exp_free(t,p)&&V(p+8)==1){int group=m->job&&V(p+0x38)==m->job;exp_top(p,generics[group],&gc[group],20);}node=V(node);}
 for(j=0;j<2;j++){gs[j][0]=0;for(i=0;i<gc[j];i++)gs[j][i+1]=gs[j][i]+V(generics[j][i]+0x48);}
 /* At fixed counts and specialties, the highest level sum maximizes the real rounded formula. */
 for(c=0;c<hn;c++){
  u32 captain=heroes[c],mates[2][2],hs[2][3],base,bonus;int hc[2]={0,0},specialist;
  if(chief&&captain!=chief)continue;
  base=exp_base(s,m,captain);bonus=exp_bonus(s,captain);specialist=m->job&&V(captain+0x38)==m->job;
  for(i=0;i<hn;i++)if(i!=c){int group=m->job&&V(heroes[i]+0x38)==m->job;exp_top(heroes[i],mates[group],&hc[group],2);}
  for(j=0;j<2;j++){hs[j][0]=0;for(i=0;i<hc[j];i++)hs[j][i+1]=hs[j][i]+V(mates[j][i]+0x48);}
  for(h0=0;h0<=hc[0];h0++)for(h1=0;h1<=hc[1]&&h0+h1<=2;h1++)
   for(g0=0;g0<=gc[0];g0++)for(g1=0;g1<=gc[1]&&g0+g1<=20;g1++){
    int n=1+h0+h1+g0+g1;u32 sum=V(captain+0x48)+hs[0][h0]+hs[1][h1]+gs[0][g0]+gs[1][g1];
    u32 chance=exp_rate(base,sum,n,g0+g1,specialist+h1+g1);
    if(chance<best_chance||(chance==best_chance&&(bonus<best_bonus||(bonus==best_bonus&&(n<best_n||(n==best_n&&sum<=best_sum))))))continue;
    best_chance=chance;best_bonus=bonus;best_n=n;best_sum=sum;list[0]=captain;k=1;
    for(i=0;i<h0;i++)list[k++]=mates[0][i];for(i=0;i<h1;i++)list[k++]=mates[1][i];
    for(i=0;i<g0;i++)list[k++]=generics[0][i];for(i=0;i<g1;i++)list[k++]=generics[1][i];
   }
 }
 return best_n;
}
static int expedition_scene(u32 mission){
    static const unsigned char scenes[]={2,1,0,4,3,3,3};
    return mission<sizeof(scenes)?scenes[mission]:-1;
}
static int exp_start(u32 parent,u32 mission,u32 ruin,u32 chief,int confirm){EXRuntime *rt=exp_get(1);EXSave *s;const EXMission *m;EXRun *r;u32 list[23],a,seed,days;int slot,n,i,generic=0;char text[384];const char *yes[]={"이 편성으로 출발","취소"};if(!rt||mission>=7||ruin>=4)return 0;s=&rt->save;m=&EX_MISSIONS[mission];days=exp_days(s,m);if(mission>=4&&!s->ruins[ruin].visited){message(parent,"먼저 해당 유적에 실제로 방문해 탐험 장소를 발견하세요.");return 0;}for(slot=0;slot<4;slot++)if(!s->runs[slot].status&&!ex_resolve(town(1),slot))break;if(slot==4){message(parent,"파견대 네 곳이 모두 사용 중입니다. 귀환 후 다시 출발할 수 있습니다.");return 0;}n=exp_party(s,chief,m,list);if(!n){message(parent,"포룸 대기 명단에 배치·보직·훈련을 맡지 않은 살아 있는 동료가 필요합니다. 비트만과 현재 영주는 파견하지 않습니다.");return 0;}chief=list[0];if(V(resource(0))<m->cost){message(parent,"파견 준비금이 부족합니다.");return 0;}r=&s->runs[slot];memset(r,0,sizeof(*r));r->mission=mission;r->ruin=ruin;r->chance=exp_chance(s,m,list,n);r->bonus=exp_bonus(s,chief);for(i=0;i<n;i++)if(V(list[i]+8)==1)generic++;FMT(text,"자동 추천 · 대장 %s / 동료 %s, %s. 영웅%d·일반%d / %d일 / 성공%d%%. 준비금%d, 성공 순수익%d~%d. 차질 지급금%d·귀환+7일·경험치1/4. 기본 개인 경험치%d. 성공률→추가금→인원수→평균 레벨 순으로 추천. 파견 중 편성·보직 불가.",(const char *)(list[0]+0x18),n-generic>1?(const char *)(list[1]+0x18):"없음",n-generic>2?(const char *)(list[2]+0x18):"없음",n-generic,generic,days,r->chance,m->cost,m->gold*(100+r->bonus)/100-m->cost,m->gold*(125+r->bonus)/100-m->cost,m->gold/2,(s->artifacts&16)?m->xp*5/4:m->xp);scene_say(parent,expedition_scene(mission),m->name,text);if(confirm&&select(parent,yes,2)!=0){memset(r,0,sizeof(*r));return 0;}a=ex_prepare(town(1),slot);if(!a){memset(r,0,sizeof(*r));message(parent,"파견 명단을 준비하지 못했습니다. 기존 인원은 변경하지 않았습니다.");return 0;}r->status=4;r->depart=now();r->due=now();for(i=0;i<n;i++)if(!ex_add(a,list[i])){if(ex_return(a))memset(r,0,sizeof(*r));message(parent,"편성을 완료하지 못해 복귀 처리했습니다. 복귀 대기가 남으면 다음 기본 화면에서 자동으로 다시 처리합니다.");return 0;}V(resource(0))-=m->cost;seed=exp_random(s);r->seed=seed;r->outcome=seed%100<r->chance?(seed%100<r->chance/4?2:1):3;r->status=1;r->due=now()+days;say(parent,m->name,"별도 파견대가 출발했습니다. 기존 9개 군단 슬롯은 사용하지 않습니다. 귀환일에 결과와 보상이 자동으로 안내됩니다.");return 1;}
static int exp_blueprint(EXSave *s){int i;for(i=0;i<3;i++)if(!(s->blueprints&(1u<<i))){s->blueprints|=1u<<i;return i+1;}return 0;}
/* All discovery criteria already exist in v0.16 saves. */
static u32 exp_design_progress(const EXSave *s,int model){
    u32 count=0;
    if(model==2)return s->completed;
    for(int i=0;i<4;i++){
        const EXVisit *v=&s->ruins[i];
        count+=(model==0?v->visited:model==1?v->used:v->story)!=0;
    }
    return count;
}
static int exp_design_available(const EXSave *s,int id){
    if(s->blueprints&(1u<<id))return 1;
    if(id<EX_STANDARD_RECIPES)return 0;
    int model=id-EX_STANDARD_RECIPES;
    return exp_design_progress(s,model)>=EX_LEGENDS[model].required;
}
static void exp_design_news(u32 parent,EXSave *s){
    char names[128],line[240];int used=0;
    for(int id=EX_STANDARD_RECIPES;id<EX_RECIPE_COUNT;id++){
        if((s->blueprints&(1u<<id))||!exp_design_available(s,id))continue;
        s->blueprints|=1u<<id;
        used+=FMT(names+used,"%s%s",used?", ":"",EX_RECIPES[id].name);
    }
    if(used){FMT(line,"%s 설계도를 얻었습니다. F8 해외 파견·유적의 장부에서 설계도 제작을 열어 확인하세요.",names);say(parent,"전설 설계도 해금",line);}
}
static u32 exp_gold(const EXRun *r){const EXMission *m=&EX_MISSIONS[r->mission];return r->outcome==3?m->gold/2:m->gold*(100+r->bonus+(r->outcome==2?25:0))/100;}
static u32 exp_xp(const EXRun *r,u32 artifacts){u32 x=EX_MISSIONS[r->mission].xp;x=r->outcome==3?x/4:r->outcome==2?x*3/2:x;return (artifacts&16)?x*5/4:x;}
static int exp_claim(u32 parent,int slot){EXRuntime *rt=exp_get(0);EXSave *s;EXRun *r;u32 a,gold,xp;char text[240];if(!rt||slot<0||slot>=4)return 0;s=&rt->save;r=&s->runs[slot];if(r->status!=3)return 0;ex_reconcile(town(1));a=ex_resolve(town(1),slot);if(!a){rt->warning=1;return 0;}if(!(r->paid&4)){if(r->mission>=4&&r->outcome!=3){EXVisit *v=&s->ruins[r->ruin];if(!v->story&&r->mission==6){const char *choices[]={"보존 · 연간 혜택 +50%","회수 · 설계도 1종"};scene_say(parent,3,EX_RUINS[r->ruin].name,"탐험대가 봉인된 보관실을 발견했습니다. 유물을 보존하면 매년 혜택이 강화되고, 회수하면 설계도를 받습니다.");{int choice=select(parent,choices,2);if(choice<0)return 0;v->story=choice==0?1:2;if(choice==1&&!exp_blueprint(s))r->extra_gold+=30000;}}if(r->mission==5)s->artifacts|=1;if(v->successes<3)v->successes++;if(v->successes>=3||(r->mission==6&&((r->seed>>8)%100)<30)){if(!exp_blueprint(s))r->extra_gold+=20000;v->successes=0;}}if(r->mission==2&&r->outcome==2)s->artifacts|=2;r->paid|=4;}gold=exp_gold(r)+r->extra_gold;xp=exp_xp(r,s->artifacts);if(!(r->paid&1)){if(!exp_credit(gold,0,0)){message(parent,"자금 보관 상한으로 정산을 기다립니다. 인원과 미지급 보상은 유지하며 다음 날 다시 시도합니다.");return 0;}r->paid|=1;}if(!(r->paid&2)){if(V(a+0x1c)&&!ex_award(a,xp,r->seed))return 0;r->paid|=2;}if(!ex_return(a)){message(parent,"포룸 대기 명단의 공간·메모리 상태로 복귀를 기다립니다. 지급한 보상은 중복 지급하지 않습니다.");return 0;}FMT(text,"%s. 지급금 %d / 기본 개인 경험치 %d. 인원은 포룸 대기 명단에 복귀했습니다. 99레벨 인원의 경험치는 성장 가능한 대원에게 균등 분배했습니다.",r->outcome==2?"대성공":r->outcome==3?"차질 후 귀환":"임무 성공",gold,xp);scene_say(parent,expedition_scene(r->mission),EX_MISSIONS[r->mission].name,text);if(r->mission>=4)message(parent,"발견한 유물·설계도와 보존 효과는 F8의 해외 파견·유적 장부에서 확인할 수 있습니다.");s->completed++;memset(r,0,sizeof(*r));exp_design_news(parent,s);return 1;}
static u32 exp_visit_army(EXVisit *v){u32 c[8];memset(c,0,sizeof(c));c[3]=v->home&65535u;c[4]=v->legion;return resolve_army(c);}
static int expedition_battle_active(void){EXRuntime *rt=exp_get(0);int i;if(!rt)return 0;for(i=0;i<4;i++)if(exp_guard_state(&rt->save.ruins[i])>=5)return 1;return 0;}
static void expedition_battle_result(void){EXRuntime *rt=exp_get(0);u32 result=G(81);int i;if(!rt||!result||(G(82)&3))return;for(i=0;i<4;i++){EXVisit *v=&rt->save.ruins[i];u32 stage=exp_guard_state(v);if(stage<5)continue;exp_guard_set(v,result==3?stage-4:4);v->seen&=~EX_SEEN_YEAR;G(81)=0;return;}}
static int exp_guard_here(EXRuntime *rt,int ruin,u32 a){u32 actor;if(!army_ok(a)||V(a+0x18)>=3)return 0;if(ruin<3)return V(a+8)==town(EX_RUINS[ruin].town);actor=V(a+0x10);return a==rt->contact_army&&actor&&V(actor+0x808)==a&&V(actor+0x34)==rt->contact_x&&V(actor+0x38)==rt->contact_y;}
static u32 exp_guard_army(u32 parent,EXRuntime *rt,int ruin){u32 list[9],t,a;const char *labels[5];char names[4][80];int i,n=0,base=0,k,choice;if(ruin==3){a=exp_visit_army(&rt->save.ruins[ruin]);if(exp_guard_here(rt,ruin,a))return a;message(parent,"월드맵 고대유적에 전투 군단으로 다시 방문하세요. 이동하거나 불러온 뒤에는 실제 유적 접촉이 필요합니다.");return 0;}t=town(EX_RUINS[ruin].town);for(i=0;t&&i<15&&n<9;i++){a=V(t+0x50654+i*4);if(exp_guard_here(rt,ruin,a)&&!exp_contains(list,n,a))list[n++]=a;}if(!n){message(parent,"해당 유적 도시에 살아 있는 군단장과 병력이 있는 아군 전투 군단이 주둔해야 합니다. 민간군단은 수호대 전투에 참여하지 않습니다.");return 0;}if(n==1)return list[0];for(;;){k=n-base;if(k>4)k=4;for(i=0;i<k;i++){a=list[base+i];FMT(names[i],"제%d군단 · 인원%d",V(a+0x14),V(a+0x1c));labels[i]=names[i];}if(base+k<n)labels[k++]="다음 군단";choice=select(parent,labels,k);if(choice<0)return 0;if(choice<4&&base+choice<n)return list[base+choice];base=base+4>=n?0:base+4;}}
static int exp_guard_start(u32 parent,int ruin,u32 a,int confirm){EXRuntime *rt=exp_get(0);EXVisit *v;const EXGuardian *g;u32 stage,home,legion;char text[640];const char *yes[]={"이 군단으로 전투 시작","취소"};if(!rt||ruin<0||ruin>=4)return 0;v=&rt->save.ruins[ruin];stage=exp_guard_state(v);if(v->visited!=exp_year()||v->used==exp_year()||stage>=3)return 0;if(expedition_battle_active()||(G(82)&3)||G(81)||G(19)||V(0x4880e0)){message(parent,"다른 전투나 본편 이벤트가 끝난 뒤 수호대에 도전하세요.");return 0;}if(!exp_guard_here(rt,ruin,a)){message(parent,"유적에 방문한 전투 군단의 주둔·위치·군단장 상태를 확인하세요.");return 0;}g=&EX_GUARDIANS[ruin*3+stage];FMT(text,"제%d군단 → %d/3단계 · 적 Lv%d. %s %s 올해 유적마다 한 번의 3단계 도전입니다. 패배·퇴각하면 올해 도전은 종료되며 실제 병력 손실이 적용됩니다. 단계 승리 후 정비하고 다시 진행할 수 있습니다. 3단계 승리 후 연간 혜택과 보물을 받습니다.",V(a+0x14),stage+1,g->level,g->summary,stage==1?"항공 수호대: 대공 무장이나 항공군단을 권장합니다.":"");scene_say(parent,2,g->name,text);if(confirm&&select(parent,yes,2)!=0)return 0;home=V(V(a+4)+4);legion=V(a+0x14);exp_guard_set(v,stage+5);G(81)=0;if(!((F2)A_BATTLE)(a,g->profile)){exp_guard_set(v,stage);message(parent,"전투를 준비하지 못했습니다. 올해 도전 기회와 기존 단계 기록은 유지합니다.");return 0;}v->home=home;exp_guard_set(v,stage+5);v->legion=legion;return 2;}
static int exp_guard_menu(u32 parent,int ruin){EXRuntime *rt=exp_get(0);EXVisit *v;u32 a,stage;if(!rt||ruin<0||ruin>=4)return 1;v=&rt->save.ruins[ruin];stage=exp_guard_state(v);if(stage==3)return 0;if(stage==4){message(parent,"이번 해의 수호대 도전은 패배·퇴각으로 종료되었습니다. 다음 게임 연도에 실제로 재방문하면 1단계부터 새로 도전할 수 있습니다.");return 1;}if(stage>=5){message(parent,"수호대 전투 결과를 확인하고 있습니다. 다른 수호대 전투를 중복 시작하지 않습니다.");return 1;}a=exp_guard_army(parent,rt,ruin);if(!a)return 1;return exp_guard_start(parent,ruin,a,1)==2?2:1;}
static int exp_bless(u32 parent,int ruin,int choice){EXRuntime *rt=exp_get(0);EXVisit *v;EXAnnualBonus bonus;u32 a,scale,tier,gold,iron,oil;int i;char text[180];if(!rt||ruin<0||ruin>=4||choice<0||choice>2)return 0;v=&rt->save.ruins[ruin];if(v->visited!=exp_year()||v->used>=exp_year()||exp_guard_state(v)!=3)return 0;tier=exp_ruin_tier(&rt->save,v);bonus=exp_ruin_bonus(&rt->save,tier);scale=v->story==1?150:100;a=exp_visit_army(v);gold=bonus.gold+(choice==0?20000*scale/100:0);iron=bonus.iron+(choice==0?20*scale/100:0);oil=bonus.oil+(choice==0?10*scale/100:0);if(V(resource(0))>2000000000u-gold||V(resource(1))>2000000000u-iron||V(resource(2))>2000000000u-oil){message(parent,"기본 혜택과 추가 보물을 보관할 자원 공간이 부족합니다. 올해 혜택과 발견 결과는 유지하며, 공간을 만든 뒤 다시 받을 수 있습니다.");return 0;}if(choice==1){if(!army_ok(a)||!ex_award(a,120*scale/100,exp_year()*31+ruin)){message(parent,"방문한 군단의 상태를 확인하거나 물자 혜택을 선택하세요. 올해 혜택과 추가 발견은 아직 사용하지 않았습니다.");return 0;}}else if(choice==2){if(!army_ok(a)){message(parent,"방문한 군단의 상태를 확인하거나 물자 혜택을 선택하세요. 올해 혜택은 아직 사용하지 않았습니다.");return 0;}for(i=0;i<81;i++){u32 p=V(a+0x60+i*4);if(alive(p))V(p+0x54)=V(p+0x58);}}exp_credit(gold,iron,oil);rt->save.artifacts|=bonus.artifact;v->used=exp_year();say(parent,EX_RUINS[ruin].name,"올해의 유적 혜택을 받았습니다. 다음 게임 연도에 다시 방문하면 새 혜택을 받을 수 있습니다.");if(tier){scene_say(parent,3,bonus.name,bonus.story);if(gold||iron||oil){FMT(text,"이번 연간 혜택 총 지급: 금 %d / 철 %d / 석유 %d. 기본 혜택과 추가 발견을 함께 정산했습니다.",gold,iron,oil);say(parent,bonus.name,text);}}exp_design_news(parent,&rt->save);return 1;}
static int exp_bless_menu(u32 parent,int ruin){const char *choices[4];char rows[3][90];EXRuntime *r=exp_get(0);u32 scale;int choice,guard;if(!r||ruin<0||ruin>=4)return 0;guard=exp_guard_menu(parent,ruin);if(guard)return guard;scale=r->save.ruins[ruin].story==1?150:100;FMT(rows[0],"물자 · 금%d/철%d/석유%d",20000*scale/100,20*scale/100,10*scale/100);FMT(rows[1],"성장 · 군단 경험치%d",120*scale/100);FMT(rows[2],"회복 · 생존 인원 HP 회복");choices[0]=rows[0];choices[1]=rows[1];choices[2]=rows[2];choices[3]="나중에";if(scale==150)message(parent,"이 유적은 보존되어 기본 물자·경험치 혜택이 50% 증가합니다.");say(parent,EX_RUINS[ruin].name,"유적마다 게임 연도에 한 번 기본 혜택을 고릅니다. 별도로 보물이나 영구 유물을 발견할 수 있습니다. 올해의 추가 발견은 재선택·저장·불러오기로 다시 추첨하지 않습니다.");choice=select(parent,choices,4);if(choice>=0&&choice<3)exp_bless(parent,ruin,choice);return 1;}
static int exp_recipe(u32 parent,int id,int confirm){
    EXRuntime *rt=exp_get(1);u32 home=town(1);
    const char *yes[]={"이 비용으로 제작 시작","취소"};char text[220];
    if(!rt||id<0||(u32)id>=EX_RECIPE_COUNT)return 0;
    EXSave *s=&rt->save;const EXRecipe *r=&EX_RECIPES[id];
    int model=id-(int)EX_STANDARD_RECIPES;
    if(model>=0){
        const EXLegend *legend=&EX_LEGENDS[model];
        scene_say(parent,6+model,r->name,legend->stats);
        u32 progress=exp_design_progress(s,model);
        if(progress>legend->required)progress=legend->required;
        FMT(text,"%s · %s %d/%d%s. 포룸 연구소와 %s LV3 완공. 금 %d / 철 %d / 석유 %d / %d일.",
            exp_design_available(s,id)?"해금":"미발견",legend->condition,progress,legend->required,legend->unit,
            r->factory==9?"차량공장":"항공기공장",r->gold,r->iron,r->oil,r->days);
        say(parent,r->name,text);
    }
    if(!exp_design_available(s,id)){
        if(model<0)message(parent,"유적 탐험에 성공해 설계도를 먼저 발견하세요.");
        return 0;
    }
    if(s->recipe){
        FMT(text,"%s 제작 대기열을 사용 중입니다. 완성까지 %d일 남았습니다.",EX_RECIPES[s->recipe-1].name,s->due>now()?s->due-now():0);
        message(parent,text);return 0;
    }
    int factory=facility(home,r->factory);
    if(r->factory==10)factory=factory||facility(home,11)||facility(home,12);
    if(!facility(home,17)||!factory){
        message(parent,model<0?"포룸에 완공된 연구소와 해당 차량·항공기 공장이 필요합니다.":"포룸에 연구소와 해당 공장 LV3를 완공한 뒤 제작하세요.");return 0;
    }
    if(V(resource(0))<r->gold||V(resource(1))<r->iron||V(resource(2))<r->oil){
        message(parent,"제작 자원이 부족합니다.");return 0;
    }
    if(model<0){
        FMT(text,"금 %d / 철 %d / 석유 %d / %d일. 완성된 기체 1대를 포룸 정비창에 인계합니다.",r->gold,r->iron,r->oil,r->days);
        say(parent,r->name,text);
    }
    if(confirm&&select(parent,yes,2)!=0)return 0;
    V(resource(0))-=r->gold;V(resource(1))-=r->iron;V(resource(2))-=r->oil;
    s->recipe=id+1;s->due=now()+r->days;s->order_retry=0;
    message(parent,"설계도 제작을 시작했습니다. 완성되면 자동으로 안내합니다.");return 1;
}
static void exp_forge(u32 parent,EXSave *s){
    const char *rows[5];char lines[4][96],status[150];int id,ans;
    if(s->recipe){
        if(now()<s->due)FMT(status,"%s 제작 중 · 완성까지 %d일.",EX_RECIPES[s->recipe-1].name,s->due-now());
        else FMT(status,"%s 완성 · 포룸 정비창 인계 대기.",EX_RECIPES[s->recipe-1].name);
        message(parent,status);
    }
    for(id=0;id<EX_STANDARD_RECIPES;id++){
        FMT(lines[id],"%s · %s",EX_RECIPES[id].name,exp_design_available(s,id)?"발견":"미발견");rows[id]=lines[id];
    }
    rows[3]="전설 설계도 4종";rows[4]="닫기";ans=select(parent,rows,5);
    if(ans==3){
        for(int model=0;model<4;model++){
            id=EX_STANDARD_RECIPES+model;
            FMT(lines[model],"%s · %s",EX_RECIPES[id].name,exp_design_available(s,id)?"해금":"미발견");rows[model]=lines[model];
        }
        ans=select(parent,rows,5);
        if(ans>=0&&ans<4)exp_recipe(parent,EX_STANDARD_RECIPES+ans,1);
    }else if(ans>=0&&ans<EX_STANDARD_RECIPES)exp_recipe(parent,ans,1);
}
static void expedition_tick(void){EXRuntime *rt=exp_get(0);int i;if(!rt)return;for(i=0;i<4;i++){EXRun *r=&rt->save.runs[i];if(r->status==1&&now()>=r->due){if(r->outcome==3){r->due+=7;r->status=now()>=r->due?3:2;r->retry=0;}else{r->status=3;r->retry=0;}}else if(r->status==2&&now()>=r->due){r->status=3;r->retry=0;}}}
static int expedition_pending(void){EXRuntime *rt=exp_get(0);int i;if(!rt)return 0;if(rt->warning)return 1;for(i=0;i<4;i++){EXRun *r=&rt->save.runs[i];EXVisit *v=&rt->save.ruins[i];if(((r->status==2&&!(r->paid&4))||r->status==3||r->status==4)&&now()>=r->retry)return 1;if(v->visited==exp_year()&&(v->seen&EX_SEEN_YEAR)<exp_year()&&v->used<exp_year())return 1;}return rt->save.recipe&&now()>=rt->save.due&&now()>=rt->save.order_retry;}
static int expedition_present(u32 parent){EXRuntime *rt=exp_get(0);int i;if(!rt)return 0;if(rt->warning){u32 warning=rt->warning;rt->warning=0;message(parent,warning==2?"저장하지 못했습니다. 기존 저장 파일은 유지되었습니다. 다시 저장해 주세요.":"파견 기록을 확인하는 과정에서 복원 문제가 발견되었습니다. 인원은 보호 복귀를 시도하며 기존 세이브 백업과 파견 장부를 확인하세요.");return 1;}for(i=0;i<4;i++){EXRun *r=&rt->save.runs[i];if(now()<r->retry)continue;if(r->status==4){u32 a;ex_reconcile(town(1));a=ex_resolve(town(1),i);if(a&&ex_return(a)){memset(r,0,sizeof(*r));message(parent,"편성 중단 또는 복구 대상 파견대가 포룸 대기 명단으로 돌아왔습니다.");}else r->retry=now()+1;return 1;}if(r->status==2&&!(r->paid&4)){r->paid|=4;scene_say(parent,expedition_scene(r->mission),EX_MISSIONS[r->mission].name,"현지 사정으로 귀환이 7일 늦어집니다. 인원은 영구 사망하지 않으며, 귀환 시 일부 지급금과 경험치를 받습니다.");return 1;}if(r->status==3){if(!exp_claim(parent,i))r->retry=now()+1;return 1;}}if(rt->save.recipe&&now()>=rt->save.due&&now()>=rt->save.order_retry){int id=rt->save.recipe-1;
    int model=id-(int)EX_STANDARD_RECIPES;
    u32 home=town(1),ok=model<0?((F2)A_GIVE_MACHINE)(home,EX_RECIPES[id].machine):((F2)A_GIVE_LEGEND)(home,model);
    if(ok==1){rt->save.recipe=rt->save.due=rt->save.order_retry=0;scene_say(parent,model<0?1:6+model,EX_RECIPES[id].name,"제작이 완료되어 포룸 정비창에 인계했습니다.");}else{rt->save.order_retry=now()+1;message(parent,"제작은 완료되었으나 정비창 인계를 기다립니다. 다음 날 자동으로 다시 시도합니다.");}return 1;}for(i=0;i<4;i++){EXVisit *v=&rt->save.ruins[i];if(v->visited==exp_year()&&(v->seen&EX_SEEN_YEAR)<exp_year()&&v->used<exp_year()){v->seen=(v->seen&~EX_SEEN_YEAR)|exp_year();exp_design_news(parent,&rt->save);exp_bless_menu(parent,i);return 1;}}return 0;}
static int exp_choose_ruin(u32 parent){EXRuntime *rt=exp_get(1);const char *labels[4];int ids[4],n=0,i,ans;if(!rt)return -1;for(i=0;i<4;i++)if(rt->save.ruins[i].visited){labels[n]=EX_RUINS[i].name;ids[n++]=i;}if(!n){message(parent,"카푸아·펠라·케브 유적 또는 월드맵 고대유적을 실제로 방문하면 탐험 장소가 등록됩니다.");return -1;}ans=select(parent,labels,n);return ans>=0&&ans<n?ids[ans]:-1;}
static void exp_send_menu(u32 parent){const char *dest[]={"엑제로스 공국 파견","동방대륙 파견","발견한 유적·갱도 탐험","닫기"};const char *labels[3];int choice,mission,ruin=0,i;choice=select(parent,dest,4);if(choice<0||choice==3)return;if(choice<2){mission=choice*2;labels[0]=EX_MISSIONS[mission].name;labels[1]=EX_MISSIONS[mission+1].name;choice=select(parent,labels,2);if(choice<0)return;mission+=choice;}else{ruin=exp_choose_ruin(parent);if(ruin<0)return;for(i=0;i<3;i++)labels[i]=EX_MISSIONS[i+4].name;choice=select(parent,labels,3);if(choice<0)return;mission=choice+4;}scene_say(parent,expedition_scene(mission),EX_MISSIONS[mission].name,EX_MISSIONS[mission].text);exp_start(parent,mission,ruin,0,1);}
static void exp_status_menu(u32 parent){EXRuntime *rt=exp_get(1);const char *labels[4],*actions[3];char rows[4][112],text[240];int i,ans,choice;u32 mission,ruin;if(!rt)return;for(i=0;i<4;i++){EXRun *r=&rt->save.runs[i];const char *status=r->status==1?"진행":r->status==2?"귀환 지연":r->status==3?"정산 대기":"복귀 중";if(r->status)FMT(rows[i],"%d · %s %d일",i+1,status,r->due>now()?r->due-now():0);else FMT(rows[i],"파견대 %d · 비어 있음",i+1);labels[i]=rows[i];}ans=select(parent,labels,4);if(ans<0||ans>=4)return;if(!rt->save.runs[ans].status){exp_send_menu(parent);return;}{EXRun *r=&rt->save.runs[ans];u32 a=ex_resolve(town(1),ans),p=a?V(a+0x34):0;mission=r->mission;ruin=r->ruin;FMT(text,"대장 %s / 인원%d / 성공%d%% / 추가금+%d%% / 남은%d일. 귀환·보상은 자동이며 같은 임무에 다른 인원을 추가 파견할 수 있습니다.",p?(const char *)(p+0x18):"복귀 확인 중",a?V(a+0x1c):0,r->chance,r->bonus,r->due>now()?r->due-now():0);say(parent,EX_MISSIONS[mission].name,text);if(r->status==3){actions[0]="정산 다시 시도";actions[1]="같은 임무 추가 파견";actions[2]="닫기";choice=select(parent,actions,3);if(choice==0){if(!exp_claim(parent,ans))r->retry=now()+1;return;}if(choice!=1)return;}else{actions[0]="같은 임무 추가 파견";actions[1]="닫기";if(select(parent,actions,2)!=0)return;}}exp_start(parent,mission,ruin,0,1);}
static int exp_ledger(u32 parent){EXRuntime *rt=exp_get(1);const char *labels[]={"유적 방문·연간 혜택","설계도 제작","수집 유물·자동 효과","닫기"};char text[220];int ans,i;if(!rt)return 0;ans=select(parent,labels,4);if(ans==0){const char *rows[4];char lines[4][100];for(i=0;i<4;i++){EXVisit *v=&rt->save.ruins[i];FMT(lines[i],"%s · %s",EX_RUINS[i].name,!v->visited?"미발견":v->used==exp_year()?"올해 사용 완료":v->visited==exp_year()?(exp_guard_state(v)==4?"올해 도전 종료":exp_guard_state(v)==3?"승리 · 혜택 가능":exp_guard_state(v)>=5?"전투 중":"수호대 도전 가능"):"올해 재방문 필요");rows[i]=lines[i];}i=select(parent,rows,4);if(i>=0){EXVisit *v=&rt->save.ruins[i];if(v->visited==exp_year()&&v->used<exp_year())return exp_bless_menu(parent,i);else message(parent,"올해 실제 방문 기록과 사용 여부를 확인하세요. 다음 연도에는 다시 방문해야 합니다.");}}else if(ans==1){exp_forge(parent,&rt->save);}else if(ans==2){const char *names[5]={"고대 나침반","상단 인장","별의 나침반","시간의 결정","현자의 서"};const char *descriptions[5]={"폐갱도 탐사 성공으로 발견합니다. 모든 유적 탐험의 성공률이 5%포인트 높아집니다. 성공률 상한은 95%입니다.","동방대륙 무역 호위 대성공으로 발견합니다. 대장 추가 지급률이 10%포인트 높아지며 대장·유물 보정의 합계 상한은 50%입니다.","연간 유적 방문의 별빛 제단에서 발견합니다. 모든 파견의 성공률이 5%포인트 높아집니다. 성공률 상한은 95%입니다.","연간 유적 방문의 별빛 제단에서 발견합니다. 앞으로 출발하는 파견의 소요 기간이 20% 줄어듭니다. 이미 출발한 파견 일정은 유지합니다.","연간 유적 방문의 별빛 제단에서 발견합니다. 파견 귀환 경험치가 25% 증가하며 99레벨 경험치 재분배에도 적용됩니다."};const char *rows[5];char lines[5][80];message(parent,"유물은 장부에 보관되며 자동 적용됩니다. 별도 장착은 필요하지 않습니다. 이름을 고르면 효과와 발견 방법을 확인할 수 있습니다.");for(i=0;i<5;i++){FMT(lines[i],"%s · %s",names[i],(rt->save.artifacts&(1u<<i))?"보유":"미발견");rows[i]=lines[i];}i=select(parent,rows,5);if(i>=0&&i<5)say(parent,names[i],descriptions[i]);message(parent,"유적의 연간 추가 발견 확률: 일반 70%, 저장고 20%, 보물 8.5%, 별빛 제단 1.4%, 왕실 보물고 0.1%. 기본 혜택은 어느 등급에서도 유지됩니다.");}return 0;}
static u32 expedition_menu(u32 parent){const char *labels[]={"파견 보내기","파견 현황·추가 파견","유적·설계도·유물 장부","닫기"};EXRuntime *rt=exp_get(1);int ans,i,active=0,found=0;char summary[220];if(!rt){message(parent,"파견 기능을 초기화하지 못했습니다. 현재 인원과 저장은 변경하지 않았습니다.");return 1;}exp_design_news(parent,&rt->save);for(i=0;i<4;i++){if(rt->save.runs[i].status)active++;if(rt->save.ruins[i].visited)found++;}FMT(summary,"별도 파견대 %d/4 사용 · 유적 %d/4 발견 · 설계도 %d/7. 임무만 고르면 포룸 대기 인원에서 대장과 동료·일반 병사를 자동 추천합니다. 확인 후 출발합니다.",active,found,pop(rt->save.blueprints));message(parent,summary);for(;;){ans=select(parent,labels,4);if(ans<0||ans==3)return 1;if(ans==0)exp_send_menu(parent);else if(ans==1)exp_status_menu(parent);else if(exp_ledger(parent)==2)return 1;}}
EXPORT void SC we_ruin_visit(u32 ctx,u32 id){EXRuntime *rt;EXVisit *v;u32 a=0,t=0,p;int i;if(!ctx||id>=4)return;p=V(ctx);if(id<3){if(!p||V(p)!=0x462738)return;t=V(p+0x50);if(!t||V(t+4)!=EX_RUINS[id].town)return;for(i=0;i<15;i++){u32 q=V(t+0x50654+i*4);if(army_ok(q)&&V(q+8)==t){a=q;break;}}}else a=V(ctx+0x1e0);if(!army_ok(a)||!V(a+4))return;rt=exp_get(1);if(!rt)return;v=&rt->save.ruins[id];{u32 stage=exp_guard_state(v);if(v->visited!=exp_year()){v->seen=0;stage=0;}v->visited=exp_year();exp_ruin_tier(&rt->save,v);if(stage!=3||v->used==exp_year()){v->home=V(V(a+4)+4);exp_guard_set(v,stage);v->legion=V(a+0x14);}if(stage<3&&v->used<exp_year())v->seen&=~EX_SEEN_YEAR;if(id==3){u32 actor=V(a+0x10);rt->contact_army=a;rt->contact_x=actor?V(actor+0x34):0;rt->contact_y=actor?V(actor+0x38):0;}}}
static void expedition_close(u32 hwnd){NoticeApi api;u32 p;if(!notice_api(&api))return;p=api.remove(hwnd,PTR(EXP_KEY));if(p)((Release)0x4500e6)(p);}
EXPORT void SC we_world_reset(void){if(MAIN_HWND)expedition_close(MAIN_HWND);}
EXPORT void SC we_load_game(u32 slot,u32 success){EXRuntime *rt;EXSave saved;int result,i;if(!success)return;rt=exp_get(1);if(!rt)return;memset(&saved,0,sizeof(saved));result=es_load(slot,&saved,sizeof(saved));memset(&rt->save,0,sizeof(rt->save));rt->save.magic=EXP_MAGIC;rt->save.version=1;rt->save.rng=0x51e7a931u^now();if(result==1&&exp_valid(&saved))memcpy(&rt->save,&saved,sizeof(saved));else if(result<0||result==1)rt->warning=1;rt->world=world();rt->contact_army=rt->contact_x=rt->contact_y=0;for(i=0;i<4;i++){EXVisit *v=&rt->save.ruins[i];u32 stage=exp_guard_state(v);if(stage>=5&&(!G(81)||(G(82)&3))){exp_guard_set(v,stage-5);v->seen&=~EX_SEEN_YEAR;}}ex_reconcile(town(1));for(i=0;i<4;i++){u32 a=ex_resolve(town(1),i);if(a&&!rt->save.runs[i].status){rt->save.runs[i].status=4;rt->save.runs[i].depart=rt->save.runs[i].due=now();}else if(!a&&rt->save.runs[i].status){memset(&rt->save.runs[i],0,sizeof(EXRun));rt->warning=1;}}}
static int exp_save_error(void){static const u16 title[]={0xc800,0xc7a5,0x20,0xc2e4,0xd328,0};static const u16 text[]={0xc800,0xc7a5,0xd558,0xc9c0,0x20,0xbabb,0xd588,0xc2b5,0xb2c8,0xb2e4,0x2e,0x20,0xae30,0xc874,0x20,0xc800,0xc7a5,0x20,0xd30c,0xc77c,0xc740,0x20,0xc720,0xc9c0,0xb418,0xc5c8,0xc2b5,0xb2c8,0xb2e4,0x2e,0x20,0xb514,0xc2a4,0xd06c,0x20,0xacf5,0xac04,0xacfc,0x20,0xd3f4,0xb354,0x20,0xc4f0,0xae30,0x20,0xad8c,0xd55c,0xc744,0x20,0xd655,0xc778,0xd55c,0x20,0xb4a4,0x20,0xb2e4,0xc2dc,0x20,0xc800,0xc7a5,0xd558,0xc138,0xc694,0x2e,0};u32 user=((F1)V(0x460060))(PTR("user32.dll")),p;if(!user)return 0;p=((F2)V(0x460100))(user,PTR("MessageBoxW"));if(!p)return 0;((F4)p)(MAIN_HWND,PTR(text),PTR(title),0x10);return 1;}
EXPORT u32 SC we_save(u32 slot){EXRuntime *rt=exp_get(1);if(!rt){exp_save_error();return 0;}if(es_save(slot,&rt->save,sizeof(rt->save)))return 1;rt->warning=exp_save_error()?0:2;return 0;}
EXPORT u32 SC we_test_ex_start(u32 mission,u32 ruin,u32 chief){return exp_start(0,mission,ruin,chief,0);}
EXPORT u32 SC we_test_ex_guardian(u32 ruin,u32 a){return exp_guard_start(0,ruin,a,0);}
EXPORT u32 SC we_test_ex_bless(u32 ruin,u32 choice){return exp_bless(0,ruin,choice);}
EXPORT u32 SC we_test_ex_recipe(u32 id){return exp_recipe(0,id,0);}
EXPORT u32 SC we_test_ex_state(void){EXRuntime *rt=exp_get(1);return rt?PTR(&rt->save):0;}
