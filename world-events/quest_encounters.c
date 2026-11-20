/* Only outstanding encounter offers use these fields. Settlement replaces them
   with the selected payout index, so the standard partial-payment flags apply. */
static void encounter_set_step(u32 *c, unsigned step){
    c[7]=(c[7]&~(3u<<16))|(step<<16);
}

static unsigned encounter_seed(u32 *c){
    unsigned seed=c[7]&65535u;
    if(!seed){
        seed=1+((F0)S_RNG)()%60000u;
        c[7]=(c[7]&~65535u)|seed;
    }
    return seed-1;
}

static int radio_encounter(u32 parent,u32 *c,unsigned seed){
    const char *places[]={"솔숲역","강나루역","채석장역","현지 기사에게 중계","나중에 듣기"};
    const char *signals[]={
        "물소리는 안 들리고 바람에 나뭇가지가 창을 긁는다.",
        "기적 다음에 뱃고동이 겹쳤다. 유리창에는 물방울이 튄다.",
        "실린 돌이 흔들리며 쨍그랑 울린다. 창밖엔 흰 가루가 날린다.",
        "승강장에는 물 대신 솔잎이 쌓였고, 짐에서는 송진 냄새가 난다.",
        "나룻배에서 등불을 흔든다. 제방에 매어 둔 밧줄이 팽팽하다.",
        "역 뒤 절벽이 온통 하얗다. 빈 돌수레들이 바람에 부딪힌다."
    };
    const char *hints[]={"역장이 소나무 아래서 깃발을 흔들고 있다.","기관사가 나룻배 이름을 읽어 주었다.","화물칸에서 석회석이 쏟아지는 소리다."};
    unsigned variant=seed%6u,target=variant%3u;
    for(;;){
        unsigned retry=(c[7]>>16)&3;
        scene_say(parent,4,"비상 수신",retry?hints[target]:signals[variant]);
        say(parent,"회신할 역",retry?"재교신에 성공하면 금 24,000. 다시 놓치거나 기사에게 맡기면 중계료 금 12,000을 받습니다.":
            "어느 역에서 보낸 신호일까요? 첫 회신은 금 36,000, 틀리면 단서를 한 번 더 듣습니다. 현지 기사에게 맡기면 금 12,000입니다.");
        int answer=select(parent,places,5);
        if(answer<0||answer>=4)return -1;
        if(answer==3)return 2;
        if((unsigned)answer==target)return retry?1:0;
        if(retry)return 2;
        encounter_set_step(c,1);
    }
}

static int salvage_encounter(u32 parent,u32 *c,unsigned seed){
    const char *survey[]={"구리 상자 회수 · 금 24,000","안쪽 지반 살피기","나중에 결정"};
    const char *descent[]={"안쪽 유물 인양 시도","구리 상자만 회수","나중에 결정"};
    int answer,stable=(seed%2u)==0;
    unsigned chance=stable?70:35;
    if(!((c[7]>>16)&3)){
        scene_say(parent,3,"인양반 보고","입구 상자는 금 24,000입니다. 안쪽을 먼저 살펴봐도 이 상자를 회수할 수 있습니다.");
        answer=select(parent,survey,3);
        if(answer==0)return 0;
        if(answer!=1)return -1;
        encounter_set_step(c,1);
    }
    scene_say(parent,3,"지반 조사",stable?
        "갱목이 단단하다. 인양 성공률은 70%. 성공하면 금 72,000과 철 30, 물이 밀려들면 금 6,000만 건진다.":
        "천장에서 모래가 샌다. 인양 성공률은 35%. 성공하면 금 72,000과 철 30, 물이 밀려들면 금 6,000만 건진다.");
    say(parent,"인양 결정","기존 병력과 자원은 안전합니다. 지금 구리 상자만 가져가면 금 24,000을 받습니다.");
    answer=select(parent,descent,3);
    if(answer==1)return 0;
    if(answer!=0)return -1;
    return (seed/2u)%100u<chance?1:2;
}

static int encore_encounter(u32 parent,u32 *c){
    const char *songs[]={"여행자의 왈츠 · 금 18,000","대장간 행진곡 · 철 35","사공의 뱃노래 · 석유 25","나중에 편성"};
    const char *setlist[4],*title="강변 악단";
    int first,second,choices[2],i,n;
    for(;;){
        first=(int)((c[7]>>16)&3)-1;
        if(first<0){
            scene_say(parent,5,title,"첫 곡을 골라 주세요. 앙코르에는 다른 곡을 골라 두 후원회의 사례를 모두 받습니다.");
            first=select(parent,songs,4);
            if(first<0||first>2)return -1;
            encounter_set_step(c,(unsigned)first+1);
        }
        say(parent,"첫 곡",songs[first]);
        say(parent,"앙코르","두 번째 곡을 고르면 악단이 연주를 시작합니다.");
        for(i=0,n=0;i<3;i++)if(i!=first){choices[n]=i;setlist[n++]=songs[i];}
        setlist[2]="첫 곡 다시 고르기";setlist[3]="나중에 편성";
        second=select(parent,setlist,4);
        if(second<0||second>2)return -1;
        if(second==2){encounter_set_step(c,0);continue;}
        /* 0+1, 0+2, 1+2 map to the three distinct pairs in the catalogue. */
        return first+choices[second]-1;
    }
}

static int encounter_choose(u32 parent,u32 *c){
    if(!c||STATUS(c)!=1)return -1;
    switch(ID(c)){
    case 38:return radio_encounter(parent,c,encounter_seed(c));
    case 39:return salvage_encounter(parent,c,encounter_seed(c));
    case 40:return encore_encounter(parent,c);
    default:return -1;
    }
}
