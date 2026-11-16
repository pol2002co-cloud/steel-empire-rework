/* Postwar event UI and objectives. All persistent writes use the reserved bank. */
typedef unsigned int u32;
typedef unsigned short u16;
#define SC __attribute__((stdcall))
#define TC __attribute__((thiscall))
#define EXPORT __declspec(dllexport)
#define V(a) (*(volatile u32 *)(u32)(a))
#define PTR(a) ((u32)(a))
typedef u32 (SC *F0)(void);
typedef u32 (SC *F1)(u32);
typedef u32 (SC *F2)(u32,u32);
typedef u32 (SC *F3)(u32,u32,u32);
typedef u32 (SC *F4)(u32,u32,u32,u32);
typedef u32 (*Allocate)(u32);
typedef void (*Release)(u32);
typedef u32 (TC *T1)(u32,u32);
typedef u32 (TC *T2)(u32,u32,u32);
typedef int (*Format)(char *,const char *,...);
typedef struct {const char *label,*result;int next,cost[3],reward[3];int cost_item,cost_count,item,item_count,machine,hire_class,hire_count,job,army_type,profile,legs,roles,project_part;u32 role_sequence;int cost_machine;} Choice;
typedef struct {const char *title,*text;const Choice *choices;int count,min_completed;} Stage;
typedef struct {const char *key,*title,*conditions;int category,kind,repeat_days,job,facility,country,min_completed;u32 dep_low,dep_high,predicates;int count;const Stage *stages;int early,goal,building,target_fixed,goal_roles;} Event;
#include "world_event_generated.h"
#define G(n) V(0x48d398+(n)*4)
static void expedition_tick(void);
static int expedition_battle_active(void);
static void expedition_battle_result(void);
static int expedition_pending(void);
static int expedition_present(u32);
static u32 expedition_menu(u32);
static void expedition_close(u32);
#define HEADPTR(t,o) V((t)+(o))
#define STAGE_REWARDED (1u<<22)
#define BATTLE_RESERVED (1u<<23)
#define DELIVERY_MACHINE_TAKEN (1u<<23)
#define SIMPLE_RULES (1u<<30)
#define SIMPLE_FORM (1u<<28)
#define LEGACY_FORM (1u<<29)
#define AUTO_BUSY (1u<<31)
/* Accepted day fits 28 bits; upper flags preserve old choice/progress layouts. */
#define OFFER_SHOWN (1u<<30)
#define READY_SHOWN (1u<<31)
#define TOUR_ENABLED (1u<<29)
#define TOUR_PERFORMED (1u<<30)
#define TOUR_REST_MASK (65535u<<13)
#define CONTROL(id,stage,status,flags) ((u32)(id)|((u32)(stage)<<8)|((u32)(status)<<16)|((u32)(flags)<<24))
#define ID(c) ((c)[0]&255)
#define STAGE(c) (((c)[0]>>8)&255)
#define STATUS(c) (((c)[0]>>16)&255)
#define FLAGS(c) ((c)[0]>>24)
#define FMT ((Format)V(0x46019c))
void *memcpy(void *dst,const void *src,u32 n){volatile unsigned char *d=dst;const volatile unsigned char *s=src;while(n--)*d++=*s++;return dst;}
void *memset(void *dst,int v,u32 n){volatile unsigned char *d=dst;while(n--)*d++=(unsigned char)v;return dst;}
static int pop(u32 x){int n=0;while(x){n++;x&=x-1;}return n;}
static u32 now(void){return V(0x48d388)/24;}
static int eid(const Event *e){return (int)(e-EVENTS);}
static u32 *card(int slot){return (u32 *)((F1)S_GETSLOT)(slot);}
static int done(int id){return ((F1)S_COMPLETED)(id)!=0;}
static int total(void){return ((F0)S_COUNT_COMPLETED)();}
static void migrate(void);
static void sync(void){
 int fresh=V(S_BASE)!=S_MAGIC;u32 day=now(),previous=V(S_LAST_DAY),tour=G(82),rest=(tour>>13)&65535;
 ((F2)S_TICK)(day,V(0x48d388)/720);
 if(fresh){G(87)=0;V(S_NEXT_OFFER)=day;}
 else if(rest&&day>=previous){u32 elapsed=day-previous;rest=rest>elapsed?rest-elapsed:0;G(82)=(G(82)&~TOUR_REST_MASK)|(rest<<13);}
 migrate();
}
static void migrate(void){int i;if(G(38)&SIMPLE_RULES)return;for(i=0;i<3;i++){u32 *c=card(i);if(!STATUS(c)||ID(c)>=WORLD_EVENT_COUNT)continue;if(STATUS(c)==1){if(c[7]&STAGE_REWARDED){c[0]=(c[0]&~(255u<<16))|(3u<<16);((F2)S_FINISH)(i,EVENTS[ID(c)].repeat_days);continue;}c[0]=CONTROL(ID(c),0,1,0);c[2]=c[3]=c[4]=c[5]=c[6]=0;c[7]=SIMPLE_FORM;}else c[7]|=LEGACY_FORM;}G(38)|=SIMPLE_RULES;}
static u32 world(void){return V(0x48c3d8);}
static u32 town_actor(int id){u32 w=world();int i;if(!w)return 0;for(i=0;i<100;i++){u32 a=V(w+0x23c+i*4);if(a&&V(a+0x7c)&&V(V(a+0x7c)+4)==(u32)id)return a;}return 0;}
static u32 town(int id){u32 a=town_actor(id);return a?V(a+0x7c):0;}
static const char *town_name(int id){u32 t=town(id);return t?(const char *)(t+0x14):"도시 없음";}
static int country(u32 t){return t?(int)V(t+8):0;}
static int region(u32 t){int c=country(t);return c>=2&&c<=11?c-2:-1;}
static u32 ui_town(u32 parent){return parent&&V(parent)==0x462738?V(parent+0x50):0;}
static int facility(u32 t,int id){
 u32 p;int last;if(!id)return 1;if(!t)return 0;if(id==20&&V(t+4)==28)return 1;
 last=id==7?9:id==13?15:id==17?18:id;
 p=((T2)0x437880)(t,id,last);
 return p&&(*(u16 *)(p+8)==1||*(u16 *)(p+8)==3);
}
static int alive(u32 p){return p&&V(p+4)==0&&(int)V(p+0x54)>0;}
static int army_ok(u32 a){return a&&V(a)==1&&V(a+0x14)>=1&&V(a+0x14)<=9&&V(a+0x1c)&&alive(V(a+0x34));}
static int has_job(u32 t,int job){int i,j;u32 h,p;int guard;if(!job)return 1;if(!t)return 0;h=V(t+0x50a58);p=h?V(h):0;guard=0;while(p&&p!=h&&guard++<10000){u32 c=V(p+8);if(c&&V(c+8)==1&&!V(c+0x10)&&alive(c)&&V(c+0x38)==(u32)job)return 1;p=V(p);}for(i=0;i<15;i++){u32 a=V(t+0x50654+i*4);if(!a||V(a)!=1||V(a+8)!=t)continue;for(j=0;j<81;j++){u32 c=V(a+0x60+j*4);if(c&&V(c+8)==1&&alive(c)&&V(c+0x38)==(u32)job)return 1;}}return 0;}
static u32 resolve_army(u32 *c){u32 w=world();int i,j;if(!w)return 0;for(i=0;i<100;i++){u32 a=V(w+0xac+i*4),t;if(a){a=V(a+0x808);if(a&&V(a)==1&&V(a+0x14)==c[4]&&V(a+4)&&V(V(a+4)+4)==c[3])return a;}a=V(w+0x23c+i*4);t=a?V(a+0x7c):0;if(!t)continue;for(j=0;j<15;j++){a=V(t+0x50654+j*4);if(a&&V(a)==1&&V(a+0x14)==c[4]&&V(a+4)&&V(V(a+4)+4)==c[3])return a;}}return 0;}
static u32 companion(int *group){u32 t=town(1),h,p;int guard=0;if(!t)return 0;h=V(t+0x50a4c);p=h?V(h):0;while(p&&p!=h&&guard++<255){u32 v=V(p+8);if(v&&alive(v)&&V(v+8)==3){int id=V(v),g=id<55?0:id<95?1:2;if(id>=14&&id<=137&&!(G(84)&(1u<<g))){*group=g;return v;}}p=V(p);}return 0;}
static int occupied(u32 t){int i;for(i=0;t&&i<15;i++){u32 a=V(t+0x50654+i*4);if(army_ok(a))return 1;}return 0;}
static int prerequisites(const Event *e,u32 t){(void)e;return t!=0;}
static int is_combat(const Event *e){int i,j;for(i=0;i<e->count;i++)for(j=0;j<e->stages[i].count;j++)if(e->stages[i].choices[j].profile)return 1;return 0;}
static int duplicate(int id){int i;for(i=0;i<3;i++)if(STATUS(card(i))&&ID(card(i))==(u32)id)return 1;return 0;}
static int acceptable_town(const Event *e,u32 t){(void)e;return t&&V(t+4)>=1&&V(t+4)<=62&&!(V(t+0x10)&1)&&(country(t)!=6||G(11)==10);}
static int origin_for(const Event *e){int i;for(i=1;i<=62;i++)if(acceptable_town(e,town(i)))return i;return 0;}
static void say(u32 parent,const char *title,const char *text){char b[152];int at=0,n,last;if(!text)return;while(text[at]){n=0;last=0;while(text[at+n]&&n<138){unsigned char ch=text[at+n];if(ch>=128){if(n>136)break;n+=2;}else{if(ch==' ')last=n;n++;}}if(text[at+n]&&last>35)n=last;memcpy(b,text+at,n);b[n++]='@';b[n++]='w';b[n]=0;((F3)UI_SPEECH)(parent,PTR(title),PTR(b));at+=n-2;while(text[at]==' ')at++;}}
static int select(u32 parent,const char **labels,int count){return ((F3)UI_SELECT)(parent,PTR(labels),count);}
static void message(u32 p,const char *s){say(p,"전역 소식",s);}
static int dist(u32 a,u32 b){int x=(int)V(a+0x34)-(int)V(b+0x34),y=(int)V(a+0x38)-(int)V(b+0x38);if(x<0)x=-x;if(y<0)y=-y;return x+y;}
static int destination(u32 *c,const Choice *ch){
 int i,best=0,score=-2147483647,from=c[2]?c[2]:c[1];
 int remaining=(c[7]>>12)&255,leg=ch->legs-remaining;
 u32 roles=ch->roles,seq=(ch->role_sequence>>(leg*4))&15,fa=town_actor(from);
 if(seq)roles=1u<<(seq-1);
 if(roles&R_HOME)return town(1)?1:0;
 if(roles&R_BLACK_POWER_HQ){fa=town_actor(63);if(!fa)return 0;}
 if(roles&R_CAPITAL)return town(40)?40:0;
 for(i=1;i<=62;i++){
  u32 a=town_actor(i),t=a?V(a+0x7c):0;int r,s,d,ok=1;
  if(!t||i==from||(i==c[1]&&ch->legs>1))continue;
  if((country(t)<1||country(t)>11)&&i!=28)continue;if(((V(a+0x14)||(V(t+0x10)&1))&&!occupied(t))||((V(t+0x10)&2)&&i!=28))continue;r=region(t);
  if(roles&R_AIRPORT)ok=facility(t,20);
  if(roles&R_LAB)ok=facility(t,17)||facility(t,18);
  if(roles&R_FACTORY)ok=facility(t,7)||facility(t,8)||facility(t,9)||facility(t,10)||facility(t,11)||facility(t,12);
  if(roles&R_DIFFERENT_COUNTRY)if(r<0||(c[7]&(1u<<r)))ok=0;
  if(!ok)continue;d=fa?dist(fa,a):1;s=(roles&R_FAR)?d:-d;
  if(s>score){score=s;best=i;}
 }
 return best;
}static u32 choose_army(u32 parent,u32 t,int type){const char *labels[5];char names[9][64];u32 list[9];int i,n=0,base=0,ans,count;for(i=0;t&&i<15&&n<9;i++){u32 a=V(t+0x50654+i*4);if(!army_ok(a)||V(a+8)!=t||(type>=0&&V(a+0x18)!=(u32)type))continue;FMT(names[n],"제%d군단 · 인원 %d",V(a+0x14),V(a+0x1c));list[n++]=a;}if(!n){message(parent,"이 도시에 조건을 만족하는 군단이 없습니다. 군단장·병력 상태와 주둔 위치를 확인하세요.");return 0;}if(n==1)return list[0];for(;;){count=n-base;if(count>4)count=4;for(i=0;i<count;i++)labels[i]=names[base+i];if(base+count<n)labels[count++]="다음 군단 목록";ans=select(parent,labels,count);if(ans<0)return 0;if(ans<4&&base+ans<n)return list[base+ans];base+=4;if(base>=n)base=0;}}
static int move(u32 parent,u32 *c){u32 a=resolve_army(c),t,actor,target,w=world();int i;if(!army_ok(a)||!c[2]||!w)return 0;target=town_actor(c[2]);if(!target)return 0;t=V(a+8);if(t){for(i=0;i<100;i++)if(!V(w+0xac+i*4))break;if(i==100)return 0;((T1)0x4382e0)(t,V(a+0x14));actor=V(a+0x10);if(!actor)return 0;}else actor=V(a+0x10);if(!actor)return 0;V(a+0x55a4)=V(actor+0x34);V(a+0x55a8)=V(actor+0x38);V(a+0x55ac)=20;((T1)0x4200a0)(actor,target);V(w+0x80)=actor;return 1;}
static const Choice *chosen(u32 *c){const Event *e;u32 s,idx;if(!c||ID(c)>=WORLD_EVENT_COUNT)return 0;e=(c[7]&LEGACY_FORM)?&LEGACY_EVENTS[ID(c)]:&EVENTS[ID(c)];s=STAGE(c);idx=(c[7]>>24)&3;if(s>=(u32)e->count||idx>=(u32)e->stages[s].count)return 0;return &e->stages[s].choices[idx];}
static void battle_result(void){u32 result=G(81),slot=G(82)&3;u32 *c;if(!result||slot<1||slot>3)return;c=card(slot-1);if(STATUS(c)==2){if(result==3){c[0]|=2u<<24;c[5]&=~READY_SHOWN;}else c[0]&=~(2u<<24);}G(81)=0;G(82)&=~3u;}
static u32 item_army(int item){int i,j;u32 w=world();if(!w)return 0;for(i=0;i<100;i++){u32 actor=V(w+0xac+i*4),a=actor?V(actor+0x808):0,t=town(i+1);if(a&&V(a)==1&&((F2)A_FIND_ITEM)(a,item))return a;for(j=0;t&&j<15;j++){a=V(t+0x50654+j*4);if(a&&V(a)==1&&((F2)A_FIND_ITEM)(a,item))return a;}}return 0;}
static int present_army(u32 t,int military){int i,found=0;if(!t||(military&&(V(t+0x10)&1)))return 0;for(i=0;i<15;i++){u32 a=V(t+0x50654+i*4);if(!a||V(a+8)!=t||!V(a+0x14)||!V(a+0x1c))continue;if(military&&V(a+0x18)==3)continue;if(V(a)!=1){if(military)return 0;continue;}if(army_ok(a))found=1;}return found;}
static int give_item_any(u32 preferred,int item){int i,j;u32 w=world();if(army_ok(preferred)&&((F2)A_GIVE_ITEM)(preferred,item)==1)return 1;if(!w)return 0;for(i=0;i<100;i++){u32 actor=V(w+0xac+i*4),a=actor?V(actor+0x808):0,t=town(i+1);if(a!=preferred&&army_ok(a)&&((F2)A_GIVE_ITEM)(a,item)==1)return 1;for(j=0;t&&j<15;j++){a=V(t+0x50654+j*4);if(a!=preferred&&army_ok(a)&&((F2)A_GIVE_ITEM)(a,item)==1)return 1;}}return 0;}
static int goal_target(u32 *c){const Event *e=&EVENTS[ID(c)];int i,j,k,n=0,choices[3]={0,0,0},scores[3]={0,0,0};u32 from=town_actor(c[1]);if(e->target_fixed)return town(e->target_fixed)?e->target_fixed:0;if(e->goal_roles&R_HOME)return town(1)?1:0;if(e->goal_roles&R_CAPITAL)return town(40)?40:0;for(i=1;i<=62;i++){u32 t=town(i),a=town_actor(i);int d;if(!t||!a||i==(int)c[1])continue;if(e->goal==6){if(!(V(t+0x10)&1)||(V(t+0x10)&2))continue;}else if(!acceptable_town(e,t)||(V(t+0x10)&2))continue;if(country(t)==6&&G(11)!=10)continue;if((e->goal_roles&R_AIRPORT)&&!facility(t,20))continue;d=from?dist(from,a):1;if(!(e->goal_roles&R_FAR))d=-d;for(j=0;j<3;j++)if(!choices[j]||d>scores[j]){for(k=2;k>j;k--){choices[k]=choices[k-1];scores[k]=scores[k-1];}choices[j]=i;scores[j]=d;if(n<3)n++;break;}}return n?choices[((F0)S_RNG)()%n]:0;}
static int goal_ready(u32 *c){const Event *e=&EVENTS[ID(c)];const Choice *ch=chosen(c);int i;if(!ch)return 0;for(i=0;i<3;i++)if(!(FLAGS(c)&1)&&V(0x46e5d8+i*4)<(u32)ch->cost[i])return 0;if(ch->cost_item&&!(FLAGS(c)&1)&&!item_army(ch->cost_item))return 0;if(ch->cost_machine&&!(c[7]&DELIVERY_MACHINE_TAKEN)&&!((F2)A_FIND_MACHINE)(town(1),ch->cost_machine))return 0;if(e->goal==1||e->goal==6){if((c[7]&LEGACY_FORM)&&(FLAGS(c)&(2|4)))return 1;if(!c[2])c[2]=goal_target(c);return c[2]&&present_army(town(c[2]),e->goal==6);}if(e->goal==5)return facility(town(1),e->building);return 1;}
static void progress(void){int i;for(i=0;i<3;i++){u32 *c=card(i);if(STATUS(c)!=2)continue;if(goal_ready(c)){c[0]=(c[0]&~(255u<<16))|(3u<<16);c[5]&=~READY_SHOWN;}}}
static u32 resource(int i){return 0x46e5d8+i*4;}
static int army_job(u32 a,int job){int i;if(!job)return 1;for(i=0;a&&i<81;i++){u32 p=V(a+0x60+i*4);if(alive(p)&&V(p+0x38)==(u32)job&&(job==9||job==10||V(p+8)==1))return 1;}return 0;}
static int healthy_for(u32 a,const Choice *ch){return army_ok(a)&&(ch->army_type<0||V(a+0x18)==(u32)ch->army_type)&&(!ch->profile||V(a+0x18)<3)&&(ch->profile!=3||(V(a+0x18)==2&&V(a+0x20)>0));}
static int major_city(u32 t){
 u32 actor;int id;if(!t)return 0;id=V(t+4);actor=town_actor(id);
 if(id<1||id>62||!actor||country(t)<1||country(t)>11)return 0;
 if(country(t)==6&&G(11)!=10)return 0;
 if(V(actor+0x14)||(V(t+0x10)&1))return 0;
 return 1;
}
static int dancers(u32 a){int i,j,n=0;u32 seen[8];for(i=0;a&&i<81&&n<8;i++){u32 p=V(a+0x60+i*4);if(!alive(p)||V(p+0x38)!=13)continue;for(j=0;j<n;j++)if(seen[j]==p)break;if(j==n)seen[n++]=p;}return n;}
static int tour_tick(u32 parent){
 u32 config=G(82),home=(config>>2)&127,legion=(config>>9)&15,c[8],a,t,selection;int i,next=0;
 (void)parent;if(!(config&TOUR_ENABLED)||(config&3)||G(19)!=0||!world())return 0;
 memset(c,0,sizeof(c));c[3]=home;c[4]=legion;a=resolve_army(c);
 if(!army_ok(a)||V(a+0x18)!=3||!dancers(a))return 0;

 if((config&TOUR_REST_MASK)||!V(a+8))return 0;t=V(a+8);
 if(major_city(t)&&!(config&TOUR_PERFORMED)){
  u32 income;if(V(0x46e5d8)>2000000000u-164800u)return 0;
  income=((F2)A_PERFORM)(a,((F0)S_RNG)());
  if(!income)return 0;V(0x46e5d8)+=income;G(82)|=TOUR_PERFORMED|(3u<<13);return 1;
 }
 for(i=1;i<=62;i++){int id=1+((int)V(t+4)+i-1)%62;if(id!=(int)V(t+4)&&major_city(town(id))){next=id;break;}}
 if(!next)return 0;c[2]=next;selection=V(world()+0x80);
 if(!move(0,c)){V(world()+0x80)=selection;return 0;}
 V(world()+0x80)=selection;G(82)&=~TOUR_PERFORMED;return 2;
}
static void tour_menu(u32 parent){
 const char *labels[]={"민간군단 지정·자동 순회 시작","자동 순회 중지","닫기"};char text[240];u32 config=G(82),t,a;int ans,count=0,i;
 if((config>>9)&15)FMT(text,"자동 순회: %s / 제%d군단 / 다음 출발까지 %d일. 비적대 일반 도시를 순회하며 최대 8명의 댄서가 공연합니다.",(config&TOUR_ENABLED)?"켜짐":"꺼짐",(config>>9)&15,(config>>13)&65535);
 else FMT(text,"자동 순회: 꺼짐 / 군단 미지정. 댄서가 있는 민간군단을 지정하세요. 시청·정부청사 건설은 필요하지 않습니다.");message(parent,text);
 ans=select(parent,labels,3);if(ans==1){G(82)&=~TOUR_ENABLED;message(parent,"자동 순회를 중지했습니다. 재시작해도 공연 대기 시간은 유지됩니다.");return;}if(ans!=0)return;
 for(i=1;i<=62;i++)if(major_city(town(i)))count++;
 if(count<2){message(parent,"진입 가능한 비적대 일반 도시가 두 곳 이상 필요합니다. 건물 완공 조건은 없습니다.");return;}
 t=ui_town(parent);if(!t)t=town(1);a=choose_army(parent,t,3);if(!army_ok(a)||!dancers(a)){message(parent,"살아 있는 댄서가 포함된 민간군단이 필요합니다. 주둔 도시 화면에서 다시 지정하세요.");return;}
 {const char *confirm[]={"이 군단의 이동·공연을 자동 관리","취소"};message(parent,"공연 뒤 3일 쉬고 다음 대도시로 실제 이동합니다. 다른 조작을 맡기려면 먼저 순회를 중지하세요.");if(select(parent,confirm,2)!=0)return;}
 G(82)=(G(82)&(TOUR_REST_MASK|TOUR_PERFORMED|AUTO_BUSY|3))|TOUR_ENABLED|((V(V(a+4)+4)&127)<<2)|((V(a+0x14)&15)<<9);
 tour_tick(parent);message(parent,"자동 순회를 시작했습니다. 진행·대기 상태와 중지는 F8의 자동 공연 메뉴에서 확인하세요.");
}
static int claim(u32 parent,int slot){
 u32 *c=card(slot),home=town(1),a;const Event *e;const Choice *ch;int i,n,level,next,r;
 if(!c||STATUS(c)!=3||ID(c)>=WORLD_EVENT_COUNT)return 0;e=&EVENTS[ID(c)];ch=chosen(c);if(!ch)return 0;
 if(!(FLAGS(c)&1)){if(!goal_ready(c))return 0;if(ch->cost_item){u32 donor=item_army(ch->cost_item);if(!donor||!((F2)A_TAKE_ITEM)(donor,ch->cost_item))return 0;}for(i=0;i<3;i++)V(resource(i))-=(u32)ch->cost[i];c[0]|=1u<<24;}

 if(ch->cost_machine&&!(c[7]&DELIVERY_MACHINE_TAKEN)){
  if(!home||!((F2)A_TAKE_MACHINE)(home,ch->cost_machine)){message(parent,"포룸 정비창에 납품 가능한 정상 미배치 장비가 없습니다. 준비한 뒤 정산하세요. 탑승·수리 중인 장비는 납품하지 않습니다.");return 0;}
  c[7]|=DELIVERY_MACHINE_TAKEN|STAGE_REWARDED;
 }
 for(i=0;i<3;i++)if(!(FLAGS(c)&(8u<<i))){u32 amount=ch->reward[i],old=V(resource(i));if(old>2000000000u||amount>2000000000u-old){message(parent,"자원 보관 상한 때문에 보상이 대기 중입니다. 자원을 사용한 뒤 다시 받으세요.");return 0;}V(resource(i))=old+amount;if(amount)c[7]|=STAGE_REWARDED;c[0]|=(8u<<i)<<24;}
 a=resolve_army(c);n=(c[7]>>20)&3;
 if(ch->item){while(n<ch->item_count){if(!give_item_any(a,ch->item)){message(parent,"아군 군단의 예비 물품 가방에 빈칸이 필요합니다. 공간이 생기면 다음 날 자동 정산합니다.");return 0;}n++;c[7]|=STAGE_REWARDED;c[7]=(c[7]&~(3u<<20))|((u32)n<<20);}}
 if(ch->hire_class){if(!home)return 0;level=1;{u32 p=V(home+0xf4);if(p&&alive(p)){u32 training=V(p+0x48);if(training>82)training=82;if(training>1)level=1+(training-1)/3;}}while(n<ch->hire_count){if(((F3)A_HIRE)(home,ch->hire_class,level)!=1){message(parent,"포룸의 병과 해금 또는 대기 인원 여유를 확인하세요. 남은 인원은 보상 대기로 유지됩니다.");return 0;}n++;c[7]|=STAGE_REWARDED;c[7]=(c[7]&~(3u<<20))|((u32)n<<20);}}
 if(ch->machine&&!(FLAGS(c)&64)){if(!home||((F2)A_GIVE_MACHINE)(home,ch->machine)!=1){message(parent,"포룸 정비창에 장비를 보관할 수 없습니다. 공간을 만든 뒤 다시 받으세요.");return 0;}c[0]|=64u<<24;c[7]|=STAGE_REWARDED;}
 say(parent,e->title,ch->result);if(ch->hire_class||ch->machine)message(parent,"고용 인원과 장비는 포룸의 대기 명단·정비창에 인계했습니다.");
 r=region(town(c[1]));if(r>=0){if(ID(c)==18||ID(c)==19||ID(c)==23)G(83)|=1u<<((ID(c)==18?0:ID(c)==19?10:20)+r);if(ID(c)==17)G(84)|=1u<<(20+r);if(ID(c)>=6&&ID(c)<=11){G(84)|=1u<<(8+r);G(87)|=2u<<(r*3);}if(ID(c)==3)G(87)|=1u<<(r*3);if(FLAGS(c)&2)G(87)|=4u<<(r*3);}
 if(ID(c)==21)G(84)|=1u<<((c[7]>>10)&3);
 ((F2)S_FINISH)(slot,e->repeat_days);return 1;
}
static int fight(u32 parent,int slot){u32 *c=card(slot),a;const Choice *ch;if(!c||STATUS(c)!=2||(G(82)&3)||expedition_battle_active())return 0;ch=chosen(c);if(!ch||!ch->profile||(FLAGS(c)&2)||(ch->legs&&!(FLAGS(c)&4)))return 0;a=resolve_army(c);if(!healthy_for(a,ch)||!V(a+8)){message(parent,"건강한 전투군단이 도시에 주둔해야 전투를 시작할 수 있습니다.");return 0;}if(!(c[7]&BATTLE_RESERVED)){if(!((F1)S_RESERVE_BATTLE)(slot)){message(parent,"이번 달의 신규 전투 계약은 이미 진행했습니다. 다음 달에 다시 시도하세요.");return 0;}c[7]|=BATTLE_RESERVED;}G(81)=0;G(82)=(G(82)&~3u)|(slot+1);if(!((F2)A_BATTLE)(a,ch->profile)){G(82)&=~3u;message(parent,"전투를 준비하지 못했습니다. 군단 상태를 확인한 뒤 재시도하세요. 이미 낸 비용은 다시 차감하지 않습니다.");return 0;}return 2;}
static int accept(u32 parent,int slot,int idx){u32 *c=card(slot);const Event *e;(void)idx;if(!c||STATUS(c)!=1||ID(c)>=WORLD_EVENT_COUNT)return 0;e=&EVENTS[ID(c)];if(!c[2]&&(e->goal==1||e->goal==6))c[2]=goal_target(c);if((e->goal==1||e->goal==6)&&!c[2]){message(parent,"현재 표시할 목적지가 없습니다. 다음 소식을 기다리세요.");return 0;}c[0]=CONTROL(ID(c),0,2,0);c[3]=c[4]=0;c[5]=now()|OFFER_SHOWN;c[6]=0;c[7]=SIMPLE_FORM;progress();if(STATUS(c)==3)return claim(parent,slot);return 1;}
static void catalog(u32 parent){
 int base=0,i,ans;const char *labels[5];char rows[3][100],buf[240];
 for(;;){for(i=0;i<3;i++){int id=base+i;if(id>=WORLD_EVENT_COUNT)break;FMT(rows[i],"%s %s [%s]",EVENTS[id].key,EVENTS[id].title,done(id)?"완료":"미완료");labels[i]=rows[i];}for(;i<3;i++)labels[i]="목록 끝";labels[3]="다음 3종";labels[4]="목록 닫기";ans=select(parent,labels,5);if(ans<0||ans==4)return;if(ans==3){base=base+3>=WORLD_EVENT_COUNT?0:base+3;continue;}if(ans>2)continue;i=base+ans;if(i>=WORLD_EVENT_COUNT)continue;say(parent,EVENTS[i].title,EVENTS[i].stages[0].text);say(parent,"목표와 보상",EVENTS[i].stages[0].choices[0].label);if(EVENTS[i].repeat_days)FMT(buf,"한 가지 목표를 달성하면 자동 완료합니다. 완료 후 %d일 뒤 다시 제안될 수 있습니다. 최초 완료 기록 %d/38종.",EVENTS[i].repeat_days,total());else FMT(buf,"한 가지 목표를 달성하면 자동 완료하는 일회성 의뢰입니다. 최초 완료 기록 %d/38종.",total());say(parent,EVENTS[i].title,buf);}
}
static int rebind(u32 parent,u32 *c){u32 t=ui_town(parent),a;const Choice *ch=chosen(c);if(!ch)return 0;if(!t)t=town(c[1]);a=choose_army(parent,t,ch->army_type);if(!healthy_for(a,ch)||!army_job(a,ch->job)||!army_job(a,EVENTS[ID(c)].job))return 0;c[3]=V(V(a+4)+4);c[4]=V(a+0x14);return 1;}
static const char *quest_building(int id){return id==6?"창고":id==17?"연구소":id==7?"차량공장":id==19?"정비창":"시설";}
static const char *quest_item(int id){return id==1?"5mm 권총":id==53?"구급상자":"예비 물품";}
static const char *quest_machine(int id){return id==6?"고블린MK2":id==1?"드래곤MK2":"일반 장비";}
static void quest_row(u32 *c,char *text){const Event *e;const Choice *ch;char goal[48],reward[48];int i,remaining;if(!c||!STATUS(c)||ID(c)>=WORLD_EVENT_COUNT){FMT(text,"빈 의뢰 칸 · 새 소식 대기");return;}e=&EVENTS[ID(c)];ch=chosen(c);if(!ch){FMT(text,"진행 기록 확인 필요");return;}if(e->goal==1)FMT(goal,"방문");else if(e->goal==6)FMT(goal,"점령");else if(e->goal==5)FMT(goal,"%s",quest_building(e->building));else if(ch->cost_machine)FMT(goal,"%s",quest_machine(ch->cost_machine));else if(ch->cost_item)FMT(goal,"물품%d개",ch->cost_count);else{for(i=0;i<3&&!ch->cost[i];i++);if(i<3)FMT(goal,"%s%d",i==0?"금":i==1?"철":"석유",ch->cost[i]);else FMT(goal,"준비");}for(i=0;i<3;i++)if(ch->reward[i]&&!(STATUS(c)==3&&(FLAGS(c)&(8u<<i))))break;if(i<3)FMT(reward,"+%s%d",i==0?"금":i==1?"철":"석유",ch->reward[i]);else if(ch->machine&&!(FLAGS(c)&64))FMT(reward,"+장비1");else if(ch->item&&(remaining=ch->item_count-((c[7]>>20)&3))>0)FMT(reward,"+물품%d",remaining);else if(ch->hire_class&&(remaining=ch->hire_count-((c[7]>>20)&3))>0)FMT(reward,"+병력%d",remaining);else FMT(reward,"완료");FMT(text,"%s %s %s %s",STATUS(c)==1?"수락":STATUS(c)==2?"진행":"정산",e->key,goal,reward);}
static void quest_progress(u32 parent,u32 *c){const Event *e=&EVENTS[ID(c)];const Choice *ch=chosen(c);char text[200];int i,prepared;if(!ch)return;if(STATUS(c)==3){message(parent,"목표 완료 · 미지급 보상을 자동 정산합니다. 이미 지급한 보상은 다시 지급하지 않습니다.");return;}if(e->goal==1||e->goal==6){if(!c[2])c[2]=goal_target(c);prepared=c[2]&&present_army(town(c[2]),e->goal==6);FMT(text,"목표 도시: %s · %s. %s",town_name(c[2]),prepared?(e->goal==6?"아군 점령 확인":"도착 확인"):(e->goal==6?"전투 군단의 점령 필요":"미도착"),e->goal==6?"원본 전투에서 승리하고 아군 전투 군단을 주둔시키세요.":"어느 아군 군단이든 실제로 도착하면 됩니다.");say(parent,"목표 진행",text);}else if(e->goal==5){FMT(text,"포룸 %s · %s. 완공하면 자동으로 완료합니다.",quest_building(e->building),facility(town(1),e->building)?"완공":"미완공");say(parent,"목표 진행",text);}if(!(FLAGS(c)&1)){for(i=0;i<3;i++)if(ch->cost[i]){u32 have=V(resource(i)),need=ch->cost[i];FMT(text,"%s %d/%d · 부족 %d",i==0?"금":i==1?"철":"석유",have,need,have<need?need-have:0);say(parent,"납품 준비",text);}if(ch->cost_item){prepared=item_army(ch->cost_item)!=0;FMT(text,"예비 %s %d/%d. 아군 어느 군단의 가방이든 인정하며 장착품은 사용하지 않습니다.",quest_item(ch->cost_item),prepared?ch->cost_count:0,ch->cost_count);say(parent,"납품 준비",text);}}else message(parent,"이 의뢰의 비용은 이미 처리했습니다. 다시 차감하지 않습니다.");if(ch->cost_machine){prepared=(c[7]&DELIVERY_MACHINE_TAKEN)||((F2)A_FIND_MACHINE)(town(1),ch->cost_machine);FMT(text,"포룸 정비창 %s %d/1. 배치·승무원을 해제하고 수리를 완료한 예비 장비 1대가 필요합니다.",quest_machine(ch->cost_machine),prepared?1:0);say(parent,"납품 준비",text);}if(c[7]&LEGACY_FORM)message(parent,"이전 버전에서 진행한 의뢰입니다. 기존 비용·선택 보상을 유지하며 현재 목표 하나만 마치면 됩니다.");}
static int quest_movable(u32 a,int military){return army_ok(a)&&V(a+4)&&(!military||V(a+0x18)!=3);}
static int quest_add_army(u32 *list,int count,u32 a,int military){int i;if(!quest_movable(a,military)||count>=9)return count;for(i=0;i<count;i++)if(list[i]==a)return count;list[count]=a;return count+1;}
static int quest_move(u32 parent,u32 *c){const Event *e=&EVENTS[ID(c)];u32 list[9],w=world(),a,temp[8];const char *labels[5],*confirm[]={"이 군단을 이동","취소"};char rows[4][92],text[180];int i,j,n=0,base=0,k,ans;if(!w||!c[2]||!town_actor(c[2]))return 0;for(i=0;i<100&&n<9;i++){u32 actor=V(w+0xac+i*4),t;if(actor)n=quest_add_army(list,n,V(actor+0x808),e->goal==6);actor=V(w+0x23c+i*4);t=actor?V(actor+0x7c):0;for(j=0;t&&j<15&&n<9;j++)n=quest_add_army(list,n,V(t+0x50654+j*4),e->goal==6);}if(!n){message(parent,e->goal==6?"이동 가능한 아군 전투 군단이 없습니다. 점령에는 민간군단을 보내지 않습니다.":"이동 가능한 아군 군단이 없습니다. 살아 있는 군단장과 병력이 있는 일반 군단이 필요합니다.");return 0;}if(n==1)a=list[0];else for(;;){k=n-base;if(k>4)k=4;for(i=0;i<k;i++){a=list[base+i];FMT(rows[i],"제%d군단 · %s",V(a+0x14),V(a+8)?town_name(V(V(a+8)+4)):"이동 중");labels[i]=rows[i];}if(base+k<n)labels[k++]="다음 군단";ans=select(parent,labels,k);if(ans<0)return 0;if(ans<4&&base+ans<n){a=list[base+ans];break;}base=base+4>=n?0:base+4;}FMT(text,"제%d군단 → %s. %s 의뢰는 이 군단에 묶이지 않습니다.",V(a+0x14),town_name(c[2]),e->goal==6?"전투·점령은 원본 규칙대로 진행합니다.":"이동 명령만 내립니다.");say(parent,"이동 명령",text);if(select(parent,confirm,2)!=0)return 0;if(V(a+8)==town(c[2])){message(parent,"이 군단은 이미 목표 도시에 주둔하고 있습니다.");return 1;}memcpy(temp,c,sizeof(temp));temp[3]=V(V(a+4)+4);temp[4]=V(a+0x14);if(!move(parent,temp)){message(parent,"군단이 출격하지 못해 이동 명령을 내리지 못했습니다. 의뢰와 담당 지정은 변경하지 않았습니다.");return 0;}message(parent,"이동 명령을 내렸습니다. 어느 아군 군단이든 목표를 달성하면 자동으로 정산합니다.");return 1;}
static int quest_abandon(u32 parent,int slot){u32 *c=card(slot);const char *confirm[]={"이 의뢰 포기","계속 진행"};if(!c||STATUS(c)!=2||!(c[7]&SIMPLE_FORM)||(c[7]&(LEGACY_FORM|STAGE_REWARDED))||(FLAGS(c)&1)){message(parent,"이미 비용·보상을 처리했거나 이전 버전에서 진행한 의뢰는 포기할 수 없습니다. 남은 목표와 보상은 유지합니다.");return 0;}message(parent,"아직 납품 비용을 지급하지 않은 의뢰입니다. 포기해도 인원·자원·완료 기록은 바뀌지 않습니다.");if(select(parent,confirm,2)!=0)return 0;return ((F1)S_CLEAR)(slot);}
static int detail(u32 parent,int slot){u32 *c=card(slot);const Event *e;const Choice *ch;const char *offer_labels[]={"이 목표 수락","나중에","소식 거절"};const char *travel_labels[]={"목표 도시로 이동","의뢰 포기","닫기"};const char *wait_labels[]={"의뢰 포기","닫기"};int ans;if(!c||!STATUS(c)||ID(c)>=WORLD_EVENT_COUNT)return 0;e=&EVENTS[ID(c)];ch=chosen(c);if(!ch)return 0;c[5]|=STATUS(c)==1?OFFER_SHOWN:READY_SHOWN;say(parent,e->title,e->stages[0].text);quest_progress(parent,c);say(parent,"목표와 보상",ch->label);if(STATUS(c)==1){ans=select(parent,offer_labels,3);if(ans==0)return accept(parent,slot,0);if(ans==2){if(c[7]&STAGE_REWARDED)message(parent,"앞 단계 보상을 지급한 의뢰는 거절할 수 없습니다. 기존 진행을 유지합니다.");else ((F1)S_CLEAR)(slot);}return 0;}if(STATUS(c)==3)return claim(parent,slot);if(e->goal==1||e->goal==6){ans=select(parent,travel_labels,3);if(ans==0)return quest_move(parent,c);if(ans==1)quest_abandon(parent,slot);}else{ans=select(parent,wait_labels,2);if(ans==0)quest_abandon(parent,slot);}return 0;}
EXPORT void SC we_tick(u32 parent){
 int i,j,id,origin;u32 *c;if(!parent||(V(parent)!=0x462738&&V(parent)!=0x461954)||!world()||G(19)!=0)return;
 sync();expedition_battle_result();if(expedition_battle_active())return;battle_result();if((G(82)&3)&&!G(81))G(82)&=~3u;progress();tour_tick(parent);expedition_tick();
 for(i=0;i<3;i++){c=card(i);if(STATUS(c)==3&&(c[5]&READY_SHOWN)&&c[6]&&now()>=c[6]){c[5]&=~READY_SHOWN;c[6]=0;}}
 if(now()<V(S_NEXT_OFFER))return;for(i=0;i<3;i++)if(STATUS(card(i))==0)break;if(i==3)return;
 id=((F0)S_RNG)()%WORLD_EVENT_COUNT;
 for(j=0;j<WORLD_EVENT_COUNT;j++,id=(id+1)%WORLD_EVENT_COUNT){const Event *e=&EVENTS[id];if(duplicate(id)||!((F3)S_CAN_OFFER)(id,e->repeat_days,is_combat(e)))continue;origin=origin_for(e);if(!origin)continue;c=card(i);memset(c,0,32);c[0]=CONTROL(id,0,1,is_combat(e)?128:0);c[1]=origin;c[7]=SIMPLE_FORM;if(e->goal==1||e->goal==6){c[2]=goal_target(c);if(!c[2]){((F1)S_CLEAR)(i);continue;}}((F1)S_SCHEDULE)(now()+7+((F0)S_RNG)()%4);return;}
 ((F1)S_SCHEDULE)(now()+1);
}
static u32 router(u32 parent){
 const char *route[]={"본편 이벤트 진행·조건","일상·후일담 전역 이벤트 38종","민간군단 도시 자동 공연","해외 파견·유적","닫기"};const char *labels[5];char rows[3][120];int ans,i;
 if(!parent||(V(parent)!=0x462738&&V(parent)!=0x461954))return 1;ans=select(parent,route,5);if(ans==0)return 0;if(ans==2){if(G(19)!=0){message(parent,"본편 이벤트가 종료된 뒤 자동 공연을 설정하세요.");return 1;}sync();tour_menu(parent);return 1;}if(ans==3){if(G(19)!=0){message(parent,"본편 대화가 종료된 뒤 파견 장부를 열어 주세요.");return 1;}sync();return expedition_menu(parent);}if(ans!=1)return 1;
 if(G(19)!=0){message(parent,"본편 이벤트 진행 중입니다. 종료한 뒤 전역 소식을 확인하세요.");return 1;}
 we_tick(parent);
 for(;;){char summary[2][80];int active=0;for(i=0;i<3;i++){u32 *c=card(i);quest_row(c,rows[i]);if(STATUS(c)&&ID(c)<WORLD_EVENT_COUNT)active++;labels[i]=rows[i];}FMT(summary[0],"전체 38종 · 완료 %d종",total());FMT(summary[1],"닫기 · 의뢰 %d/3",active);labels[3]=summary[0];labels[4]=summary[1];ans=select(parent,labels,5);if(ans<0||ans==4)return 1;if(ans==3){catalog(parent);continue;}if(ans>=0&&ans<3&&detail(parent,ans)==2)return 1;}
}
EXPORT u32 SC we_test_accept(u32 parent,u32 slot,u32 choice){sync();return accept(parent,slot,choice);}
EXPORT u32 SC we_test_claim(u32 parent,u32 slot){sync();return claim(parent,slot);}
EXPORT void SC we_test_progress(void){expedition_battle_result();battle_result();progress();}
EXPORT u32 SC we_test_prerequisite(u32 id,u32 townid){if(id>=WORLD_EVENT_COUNT)return 0;sync();return acceptable_town(&EVENTS[id],town(townid));}

EXPORT u32 SC we_test_tour(u32 parent){sync();return tour_tick(parent);}

EXPORT u32 SC we_router(u32 parent){
 u32 result;if(!parent||(V(parent)!=0x462738&&V(parent)!=0x461954)||!world())return 1;
 if(V(S_BASE)!=S_MAGIC)sync();if((G(82)&AUTO_BUSY)||expedition_battle_active())return 1;G(82)|=AUTO_BUSY;
 result=router(parent);G(82)&=~AUTO_BUSY;return result;
}
/* The toolbar consumes this frame after opening native dialogue or a battle. */
EXPORT u32 SC we_present(u32 parent){
 int pass,i,shown=0;
 if(!parent||(V(parent)!=0x462738&&V(parent)!=0x461954)||!world()||G(19)||V(0x4880e0))return 0;
 if(V(S_BASE)==S_MAGIC&&(G(82)&AUTO_BUSY))return 1;
 we_tick(parent);if(expedition_battle_active())return 1;G(82)|=AUTO_BUSY;
 for(pass=0;pass<3&&!shown;pass++)for(i=0;i<3&&!shown;i++){
  u32 *c=card(i),a,t;const Choice *ch;const Event *e;const char *labels[2];char intro[240];int type=pass==0?3:pass==1?2:1,ans;
  if(!c||STATUS(c)!=(u32)type||ID(c)>=WORLD_EVENT_COUNT)continue;
  e=&EVENTS[ID(c)];if(!e->early&&G(11)!=10)continue;
  if(c[5]&(type==1?OFFER_SHOWN:READY_SHOWN))continue;
  if(type==2)continue;
  if(type==2){
   ch=chosen(c);a=resolve_army(c);t=army_ok(a)?V(a+8):0;
   if(!ch||!t)continue;
   if(!((ch->profile&&!(FLAGS(c)&2)&&(!ch->legs||(FLAGS(c)&4)))||(ch->legs&&c[2]&&V(t+4)!=c[2])))continue;
  }
  c[5]|=type==1?OFFER_SHOWN:READY_SHOWN;shown=1;
  if(type==3){if(!claim(parent,i))c[6]=now()+1;continue;}
  FMT(intro,"%s에서 %s 소식이 도착했습니다. %s",town_name(c[1]),e->title,type==1?"지금 이야기를 듣고 진행 방법을 선택할 수 있습니다.":type==3?"목표를 달성했습니다. 결과와 보상을 확인할 수 있습니다.":"담당 군단이 도착했습니다. 다음 진행을 선택할 수 있습니다.");
  say(parent,e->title,intro);labels[0]=type==1?"지금 이야기 듣기":type==3?"결과 확인·보상 정산":c[2]?"다음 목적지로 자동 출발":"전투 시작";labels[1]="나중에 확인 · F8에 보관";
  ans=select(parent,labels,2);
  if(ans==0){if(type==3)claim(parent,i);else if(type==1)detail(parent,i);else if(c[2]){if(!move(parent,c))message(parent,"지금 출발하지 못했습니다. F8의 해당 소식에서 군단 상태를 확인하고 다시 출발할 수 있습니다.");}else fight(parent,i);}
 }
 G(82)&=~AUTO_BUSY;return shown;
}

/* Per-window transient state never enters a save; no modal UI runs from draw/update. */
typedef struct {u32 parent,generation,queued,handling,armed_at;} NoticeQueue;
typedef struct {F2 get;F3 set;F2 remove;F4 post;F0 ticks;} NoticeApi;
#define NOTICE_MESSAGE 0x86e0u
#define MAIN_HWND V(0x476fe8)
#define NOTICE_KEY "SteelEmpireRework.NoticeQueue.0113"
#define LOADING_KEY "SteelEmpireRework.NoticeLoading.0113"
#define TRAINING_KEY "SteelEmpireRework.TrainingCompleted.0121"
static int notice_api(NoticeApi *api){
 u32 user=((F1)V(0x460060))(PTR("user32.dll")),kernel=((F1)V(0x460060))(PTR("kernel32.dll"));
 if(!user||!kernel)return 0;
 api->get=(F2)((F2)V(0x460100))(user,PTR("GetPropA"));
 api->set=(F3)((F2)V(0x460100))(user,PTR("SetPropA"));
 api->remove=(F2)((F2)V(0x460100))(user,PTR("RemovePropA"));
 api->post=(F4)((F2)V(0x460100))(user,PTR("PostMessageA"));
 api->ticks=(F0)((F2)V(0x460100))(kernel,PTR("GetTickCount"));
 return api->get&&api->set&&api->remove&&api->post&&api->ticks;
}
static NoticeQueue *notice_state(NoticeApi *api,u32 hwnd,int create){
 NoticeQueue *s=(NoticeQueue *)api->get(hwnd,PTR(NOTICE_KEY));
 if(!s&&create){s=(NoticeQueue *)((Allocate)0x450452)(sizeof(NoticeQueue));if(!s)return 0;memset(s,0,sizeof(*s));s->armed_at=api->ticks();if(!api->set(hwnd,PTR(NOTICE_KEY),PTR(s))){((Release)0x4500e6)(PTR(s));return 0;}}
 return s;
}
static int notice_parent(u32 parent){
 u32 controller=V(0x48cc1c);
 if(!controller||V(controller+4)!=3||V(controller+0x10)!=parent)return 0;
 if(!parent||(V(parent)!=0x462738&&V(parent)!=0x461954))return 0;
 return world()&&!G(19)&&!V(0x4880e0);
}
static void notice_reset(NoticeQueue *s,NoticeApi *api){if(s){s->generation++;s->parent=0;s->queued=0;s->armed_at=api->ticks();}}
EXPORT void SC we_training_done(u32 t){NoticeApi api;u32 hwnd=MAIN_HWND,n;if(!t||(V(t+0x10)&1))return;if(!hwnd||!notice_api(&api)||api.get(hwnd,PTR(LOADING_KEY)))return;n=api.get(hwnd,PTR(TRAINING_KEY));if(n<10000)api.set(hwnd,PTR(TRAINING_KEY),n+1);}
EXPORT void SC we_load_begin(void){NoticeApi api;NoticeQueue *s;u32 hwnd=MAIN_HWND;if(!hwnd||!notice_api(&api))return;api.set(hwnd,PTR(LOADING_KEY),1);api.remove(hwnd,PTR(TRAINING_KEY));s=notice_state(&api,hwnd,0);notice_reset(s,&api);}
EXPORT void SC we_load_end(void){NoticeApi api;u32 hwnd=MAIN_HWND;if(V(S_BASE)==S_MAGIC)G(82)&=~AUTO_BUSY;if(!hwnd||!notice_api(&api))return;api.remove(hwnd,PTR(LOADING_KEY));api.remove(hwnd,PTR(TRAINING_KEY));notice_reset(notice_state(&api,hwnd,0),&api);}
EXPORT void SC we_window_close(u32 hwnd){NoticeApi api;NoticeQueue *s;if(!notice_api(&api))return;expedition_close(hwnd);s=(NoticeQueue *)api.remove(hwnd,PTR(NOTICE_KEY));api.remove(hwnd,PTR(LOADING_KEY));api.remove(hwnd,PTR(TRAINING_KEY));if(s)((Release)0x4500e6)(PTR(s));}
EXPORT u32 SC we_idle(u32 parent){
 NoticeApi api;NoticeQueue *s;u32 hwnd=MAIN_HWND,ticks;int i,pending=0;
 if(!hwnd||!notice_parent(parent)||!notice_api(&api)||api.get(hwnd,PTR(LOADING_KEY)))return 0;
 s=notice_state(&api,hwnd,1);if(!s)return 0;if(s->handling)return 1;
 ticks=api.ticks();if(s->parent!=parent){notice_reset(s,&api);s->parent=parent;return 0;}
 if((u32)(ticks-s->armed_at)<1000)return 0;
 we_tick(parent);if(s->queued)return 0;
 for(i=0;i<3;i++){u32 *c=card(i),type=STATUS(c);if(ID(c)<WORLD_EVENT_COUNT&&(type==1||type==3)&&!(c[5]&(type==1?OFFER_SHOWN:READY_SHOWN))){pending=1;break;}}
 if(!pending)pending=api.get(hwnd,PTR(TRAINING_KEY))!=0;
 if(!pending)pending=expedition_pending();
 if(!pending)return 0;s->generation++;s->queued=1;
 if(!api.post(hwnd,NOTICE_MESSAGE,s->generation,parent))s->queued=0;
 return 0;
}
EXPORT u32 SC we_message(u32 hwnd,u32 message,u32 generation,u32 parent){
 NoticeApi api;NoticeQueue *s;
 if(message!=NOTICE_MESSAGE||hwnd!=MAIN_HWND||!notice_api(&api))return 0;
 s=notice_state(&api,hwnd,0);if(!s||!s->queued||s->generation!=generation||s->parent!=parent)return 0;
 s->queued=0;
 if(s->handling||api.get(hwnd,PTR(LOADING_KEY))||!notice_parent(parent))return 0;
 if((u32)(api.ticks()-s->armed_at)<1000)return 0;
 s->handling=1;
 {u32 count=api.remove(hwnd,PTR(TRAINING_KEY));if(count){char text[180];G(82)|=AUTO_BUSY;FMT(text,"재훈련이 완료되었습니다. 총 %d명이 재훈련을 마쳤습니다. 해당 도시의 대기 명단에서 확인할 수 있습니다.",count);say(parent,"재훈련 완료",text);G(82)&=~AUTO_BUSY;}else{int shown;G(82)|=AUTO_BUSY;shown=expedition_present(parent);G(82)&=~AUTO_BUSY;if(!shown)we_present(parent);}}
 if(api.get(hwnd,PTR(NOTICE_KEY))==PTR(s)){s->handling=0;s->armed_at=api.ticks();}
 return 0;
}
