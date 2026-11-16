/* Own metadata only; never store native pointers or character images here. */
#ifndef STEEL_EXPEDITION_STORAGE_H
#define STEEL_EXPEDITION_STORAGE_H
typedef unsigned char ESByte;
typedef u32 (SC *ESCreate)(u32,u32,u32,u32,u32,u32,u32);
typedef u32 (SC *ESIO)(u32,u32,u32,u32,u32);
typedef struct {ESCreate open;ESIO read,write;F4 seek,temp;F2 size;F1 flush,close,remove;F3 replace;} ESApi;
typedef struct {u32 magic0,magic1,version,length,base_size,header_crc,payload_crc,footer_crc;} ESFooter;
#define ES_MAGIC0 0x58504553u
#define ES_MAGIC1 0x31564153u
#define ES_MAX 8192u
#define ES_FILE_MAX (64u*1024u*1024u)
#define ES_BAD_HANDLE 0xffffffffu
static u32 es_crc(const void *data,u32 n){const ESByte *p=data;u32 c=0xffffffffu,i;while(n--){c^=*p++;for(i=0;i<8;i++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return c^0xffffffffu;}
static int es_api(ESApi *a){
 u32 k=((F1)V(0x460060))(PTR("kernel32.dll"));if(!k)return 0;
#define ES_PROC(field,type,name) a->field=(type)((F2)V(0x460100))(k,PTR(name))
 ES_PROC(open,ESCreate,"CreateFileA");ES_PROC(read,ESIO,"ReadFile");ES_PROC(write,ESIO,"WriteFile");
 ES_PROC(seek,F4,"SetFilePointer");ES_PROC(size,F2,"GetFileSize");ES_PROC(flush,F1,"FlushFileBuffers");
 ES_PROC(close,F1,"CloseHandle");ES_PROC(remove,F1,"DeleteFileA");ES_PROC(replace,F3,"MoveFileExA");ES_PROC(temp,F4,"GetTempFileNameA");
#undef ES_PROC
 return a->open&&a->read&&a->write&&a->seek&&a->size&&a->flush&&a->close&&a->remove&&a->replace&&a->temp;
}
static int es_read(ESApi *a,u32 h,u32 position,void *data,u32 n){u32 got=0;return a->seek(h,position,0,0)==position&&a->read(h,PTR(data),n,PTR(&got),0)&&got==n;}
static int es_write(ESApi *a,u32 h,const void *data,u32 n){u32 wrote=0;return a->write(h,PTR(data),n,PTR(&wrote),0)&&wrote==n;}
static const char *es_filename(u32 slot){return slot<6?(const char *)V(0x469060+slot*4):0;}
/* The native writer sees a temporary path, so a failed appendix cannot erase a slot. */
static int es_save(u32 slot,const void *state,u32 n){
 ESApi api;ESFooter f;char temp[260],dir[260];ESByte header[16];u32 i,last=0,h=ES_BAD_HANDLE,size=0;int ok=0;
 const char *dest=es_filename(slot);typedef u32 (*ESSave)(u32,const char *);
 if(!dest||!state||!n||n>ES_MAX||(n&3)||!es_api(&api))return 0;
 for(i=0;dest[i];i++){if(i>=258)return 0;if(dest[i]=='\\'||dest[i]=='/')last=i+1;}
 if(last){for(i=0;i<last;i++)dir[i]=dest[i];dir[last]=0;}else{dir[0]='.';dir[1]=0;}
 if(!api.temp(PTR(dir),PTR("SEP"),0,PTR(temp)))return 0;
 if(!((ESSave)E_NATIVE_SAVE)(slot,temp))goto done;
 h=api.open(PTR(temp),0xc0000000u,0,0,3,0x80,0);if(h==ES_BAD_HANDLE)goto done;
 size=api.size(h,0);if(size<1024||size>ES_FILE_MAX-n-sizeof(f)||!es_read(&api,h,0,header,16))goto done;
 f.magic0=ES_MAGIC0;f.magic1=ES_MAGIC1;f.version=1;f.length=n;f.base_size=size;
 f.header_crc=es_crc(header,16);f.payload_crc=es_crc(state,n);f.footer_crc=es_crc(&f,28);
 if(api.seek(h,size,0,0)!=size||!es_write(&api,h,state,n)||!es_write(&api,h,&f,sizeof(f))||!api.flush(h))goto done;
 if(!api.close(h))goto done;h=ES_BAD_HANDLE;
 if(!api.replace(PTR(temp),PTR(dest),9))goto done;
 ok=1;
done:
 if(h!=ES_BAD_HANDLE)api.close(h);
 if(!ok)api.remove(PTR(temp));
 return ok;
}
/* Return0 only for an old save without our footer; leave destination untouched on failure. */
static int es_load(u32 slot,void *state,u32 n){
 ESApi api;ESFooter f;ESByte header[16],*copy=0;u32 h=ES_BAD_HANDLE,size,i;int result=-1;const char *filename=es_filename(slot);
 if(!filename||!state||!n||n>ES_MAX||(n&3)||!es_api(&api))return -1;
 h=api.open(PTR(filename),0x80000000u,1,0,3,0x80,0);if(h==ES_BAD_HANDLE)return -1;
 size=api.size(h,0);if(size<1024||size>ES_FILE_MAX)goto done;
 if(!es_read(&api,h,size-sizeof(f),&f,sizeof(f)))goto done;
 if(f.magic0!=ES_MAGIC0||f.magic1!=ES_MAGIC1){result=(f.magic0==ES_MAGIC0||f.magic1==ES_MAGIC1)?-1:0;goto done;}
 if(f.version!=1||f.length!=n||f.base_size<1024||f.base_size>ES_FILE_MAX||f.base_size+n+sizeof(f)!=size||f.footer_crc!=es_crc(&f,28))goto done;
 if(!es_read(&api,h,0,header,16)||f.header_crc!=es_crc(header,16))goto done;
 copy=(ESByte *)((Allocate)0x450452)(n);if(!copy)goto done;
 if(!es_read(&api,h,f.base_size,copy,n)||f.payload_crc!=es_crc(copy,n))goto done;
 for(i=0;i<n;i++)((ESByte *)state)[i]=copy[i];result=1;
done:
 if(copy)((Release)0x4500e6)(PTR(copy));
 if(h!=ES_BAD_HANDLE)api.close(h);
 return result;
}
#endif
