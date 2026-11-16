"""Hidden native rosters10..13, kept off the map and outside ordinary nine armies.

The source is linked into the existing readonly C image, avoiding another image.
Native town/army/person codecs persist every member and equipped item unchanged.
"""
EXPORTS=('ex_resolve','ex_prepare','ex_add','ex_return','ex_award','ex_reconcile')
MAGIC=0x45585031
PROTOTYPES='''
__declspec(dllexport) unsigned __attribute__((stdcall)) ex_resolve(unsigned,unsigned);
__declspec(dllexport) unsigned __attribute__((stdcall)) ex_prepare(unsigned,unsigned);
__declspec(dllexport) unsigned __attribute__((stdcall)) ex_add(unsigned,unsigned);
__declspec(dllexport) unsigned __attribute__((stdcall)) ex_return(unsigned);
__declspec(dllexport) unsigned __attribute__((stdcall)) ex_award(unsigned,unsigned,unsigned);
__declspec(dllexport) unsigned __attribute__((stdcall)) ex_reconcile(unsigned);
'''
SOURCE=r'''
typedef unsigned int ex_u32;
#define EXV(a) (*(volatile ex_u32 *)(ex_u32)(a))
#define EXSC __attribute__((stdcall))
#define EXEXPORT __declspec(dllexport)
typedef ex_u32 (*ExAlloc)(ex_u32);
typedef void (*ExFree)(ex_u32);
typedef ex_u32 (__attribute__((thiscall)) *ExCreate)(ex_u32,ex_u32,ex_u32);
typedef void (__attribute__((thiscall)) *ExRegister)(ex_u32,ex_u32,ex_u32,ex_u32,ex_u32);
typedef void (__attribute__((thiscall)) *ExXp)(ex_u32,ex_u32);
typedef ex_u32 (*ExThread)(void);
#define EXMAGIC 0x45585031u
static int ex_home(ex_u32 t){return t&&EXV(t+4)==1&&EXV(t+8)==1;}
static ex_u32 ex_address(ex_u32 t,ex_u32 slot){return t+0x104+(slot+9)*0x55b0;}
static int ex_owned(ex_u32 t,ex_u32 a){ex_u32 n;if(!ex_home(t)||!a||EXV(a+4)!=t)return 0;n=EXV(a+0x14);return n>=10&&n<=13&&a==ex_address(t,n-10)&&EXV(a)==1&&EXV(a+0x18)==3&&EXV(a+0x55ac)==EXMAGIC;}
static int ex_links(ex_u32 head,ex_u32 node){ex_u32 next,prev;if(!head||!node)return 0;next=EXV(node);prev=EXV(node+4);return next&&prev&&EXV(next+4)==node&&EXV(prev)==node;}
static ex_u32 ex_node(ex_u32 head,ex_u32 person,ex_u32 count){ex_u32 p,i;if(!head||count>10000||!ex_links(head,head))return 0;p=EXV(head);for(i=0;p&&p!=head&&i<count;i++){if(!ex_links(head,p))return 0;if(EXV(p+8)==person)return p;p=EXV(p);}return 0;}
static int ex_master(ex_u32 t,ex_u32 p){return ex_node(EXV(t+0x50a4c),p,EXV(t+0x50a50))!=0;}
static int ex_other(ex_u32 t,ex_u32 a,ex_u32 p){int i,j;for(i=0;i<15;i++){ex_u32 b=t+0x104+i*0x55b0;if(b==a||!EXV(b+0x14))continue;for(j=0;j<81;j++)if(EXV(b+0x60+j*4)==p)return 1;}return 0;}
static int ex_free_person(ex_u32 t,ex_u32 p){ex_u32 kind;if(!p||p==EXV(t+0xa0)||EXV(p)==14)return 0;kind=EXV(p+8);if(kind!=1&&kind!=3)return 0;if(EXV(p+4)||EXV(p+0x10)||EXV(p+0x14)||(int)EXV(p+0x54)<=0)return 0;if(EXV(p+0x38)<1||EXV(p+0x38)>13||EXV(p+0x48)<1||EXV(p+0x48)>99)return 0;return kind==3?ex_master(t,p):ex_node(EXV(t+0x50a58),p,EXV(t+0x50a5c))!=0;}
static int ex_roster(ex_u32 t,ex_u32 a){int i,j,n=0;if(!ex_owned(t,a)||EXV(a+8)||EXV(a+0xc)||EXV(a+0x10)||EXV(a+0x20))return 0;for(i=0;i<9;i++)if(EXV(a+0x3c+i*4))return 0;for(i=0;i<81;i++){ex_u32 p=EXV(a+0x60+i*4);if(!p)continue;if(EXV(p+8)!=1&&EXV(p+8)!=3)return 0;for(j=0;j<i;j++)if(EXV(a+0x60+j*4)==p)return 0;n++;}return n<=23&&EXV(a+0x1c)==(ex_u32)n;}
EXEXPORT ex_u32 EXSC ex_resolve(ex_u32 t,ex_u32 slot){ex_u32 a;if(!ex_home(t)||slot>=4)return 0;a=ex_address(t,slot);return ex_roster(t,a)?a:0;}
EXEXPORT ex_u32 EXSC ex_prepare(ex_u32 t,ex_u32 slot){ex_u32 a;if(!ex_home(t)||slot>=4)return 0;a=ex_address(t,slot);if(EXV(a+0x14))return 0;a=((ExCreate)0x437be0)(t,slot+10,3);if(!a)return 0;EXV(a+0x55ac)=EXMAGIC;return a;}
EXEXPORT ex_u32 EXSC ex_add(ex_u32 a,ex_u32 p){ex_u32 t,kind,node=0,index=81;int i,n=0;if(!a)return 0;t=EXV(a+4);if(!ex_roster(t,a)||!ex_free_person(t,p)||ex_other(t,a,p))return 0;kind=EXV(p+8);for(i=0;i<81;i++){ex_u32 q=EXV(a+0x60+i*4);if(q==p)return 0;if(q&&EXV(q+8)==kind)n++;}if(kind==3){if(n>=3)return 0;for(i=39;i<=41;i++)if(!EXV(a+0x60+i*4)){index=i;break;}}else{if(n>=20)return 0;for(i=0;i<20;i++)if(!EXV(a+0x60+i*4)){index=i;break;}node=ex_node(EXV(t+0x50a58),p,EXV(t+0x50a5c));if(!node)return 0;}if(index>=81)return 0;EXV(a+0x60+index*4)=p;EXV(a+0x1c)++;EXV(p+4)=2;EXV(p+0x10)=EXV(a+0x14);EXV(p+0x14)=0;if(kind==3){if(!EXV(a+0x34))EXV(a+0x34)=p;if(index==41)EXV(a+0x38)=p;}else{ex_u32 next=EXV(node),prev=EXV(node+4);EXV(prev)=next;EXV(next+4)=prev;EXV(t+0x50a5c)--;((ExFree)0x4500e6)(node);}return 1;}
EXEXPORT ex_u32 EXSC ex_return(ex_u32 a){ex_u32 t,head,nodes[20],people[20],made=0;int i,j;if(!a)return 0;t=EXV(a+4);if(!ex_roster(t,a))return 0;head=EXV(t+0x50a58);if(!head||!ex_links(head,head)||EXV(t+0x50a5c)>10000)return 0;for(i=0;i<81;i++){ex_u32 p=EXV(a+0x60+i*4);if(!p)continue;if(EXV(p+0x10)!=EXV(a+0x14)||EXV(p+0x14)||ex_other(t,a,p))goto failed;if(EXV(p+8)==3){if(!ex_master(t,p))goto failed;}else{if(made>=20||EXV(t+0x50a5c)+made+1>10000||ex_node(head,p,EXV(t+0x50a5c)))goto failed;nodes[made]=((ExAlloc)0x450452)(12);if(!nodes[made])goto failed;people[made]=p;made++;}}for(i=0;i<(int)made;i++){ex_u32 tail=EXV(head+4),node=nodes[i];EXV(node)=head;EXV(node+4)=tail;EXV(node+8)=people[i];EXV(tail)=node;EXV(head+4)=node;EXV(t+0x50a5c)++;}for(i=0;i<81;i++){ex_u32 p=EXV(a+0x60+i*4);if(!p)continue;EXV(p+0x10)=0;if(EXV(p+4)==2)EXV(p+4)=0;if(EXV(p+8)==3&&EXV(p+4)!=1)((ExRegister)0x438760)(t,3,0,0,p);EXV(a+0x60+i*4)=0;}EXV(a+0x34)=EXV(a+0x38)=EXV(a+0x1c)=EXV(a+0x14)=EXV(a+0x55ac)=0;return 1;
 failed:for(j=0;j<(int)made;j++)((ExFree)0x4500e6)(nodes[j]);return 0;}
EXEXPORT ex_u32 EXSC ex_award(ex_u32 a,ex_u32 per,ex_u32 seed){ex_u32 list[81],n=0,eligible=0,total,base,extra,tls,old;int i,j;if(!a||EXV(a)!=1||!EXV(a+0x14)||per>100000)return 0;if(EXV(a+0x14)>9&&!ex_roster(EXV(a+4),a))return 0;for(i=0;i<81;i++){ex_u32 p=EXV(a+0x60+i*4);if(!p)continue;if(EXV(p+8)!=1&&EXV(p+8)!=3)continue;if((int)EXV(p+0x54)<=0||EXV(p+4)==1||(EXV(a+0x14)<=9&&EXV(p+4)!=0))continue;if(EXV(p+0x48)<1||EXV(p+0x48)>99||EXV(p+0x38)<1||EXV(p+0x38)>13||(int)EXV(p+0x4c)<0||(int)EXV(p+0x50)<=0)return 0;for(j=0;j<(int)n;j++)if(list[j]==p)break;if(j<(int)n)continue;list[n++]=p;if(EXV(p+0x48)<99)eligible++;}if(!n)return 0;if(!eligible||!per)return 1;total=per*n;base=total/eligible;extra=total%eligible;for(i=0;i<(int)n;i++)if(EXV(list[i]+0x48)<99&&EXV(list[i]+0x4c)>0x7fffffffu-base-1)return 0;tls=((ExThread)0x45290b)();if(!tls)return 0;old=EXV(tls+0x14);EXV(tls+0x14)=seed;for(i=0;i<(int)n;i++){ex_u32 p=list[i];if(EXV(p+0x48)>=99)continue;EXV(p+0x4c)+=base+(extra?1:0);if(extra)extra--;((ExXp)0x414fc0)(EXV(0x4880e8),p);}EXV(tls+0x14)=old;return 1;}
EXEXPORT ex_u32 EXSC ex_reconcile(ex_u32 t){int slot,i,n=0;if(!ex_home(t))return 0;for(slot=0;slot<4;slot++){ex_u32 a=ex_resolve(t,slot),chief=0,count=0;if(!a)continue;for(i=0;i<81;i++){ex_u32 p=EXV(a+0x60+i*4);if(!p)continue;if(ex_other(t,a,p)||(EXV(p+8)==3&&(!ex_master(t,p)||p==EXV(t+0xa0)||EXV(p)==14||EXV(p+0x14)||(EXV(p+0x10)&&EXV(p+0x10)!=EXV(a+0x14))))){EXV(a+0x60+i*4)=0;continue;}if(EXV(p+8)==1&&ex_node(EXV(t+0x50a58),p,EXV(t+0x50a5c))){EXV(a+0x60+i*4)=0;continue;}EXV(p+0x10)=EXV(a+0x14);if(EXV(p+4)==0)EXV(p+4)=2;if(EXV(p+8)==3&&!chief)chief=p;count++;}EXV(a+0x34)=chief;EXV(a+0x38)=0;EXV(a+0x1c)=count;n++;}return n;}
'''
