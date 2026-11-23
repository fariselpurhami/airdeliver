// Preserve the request origin only behind the checked development gateway.
import { handlers } from '@/auth';
import { NextRequest } from 'next/server';
function externalRequest(req: NextRequest) {
 if(process.env.NODE_ENV!=='development' || process.env.DEV_LAN_GATEWAY!=='true')return req;
 const host=req.headers.get('x-forwarded-host');
 if(!host)return req;
 const url=new URL(req.url);url.host=host;url.protocol='http:';
 return new NextRequest(url,req);
}
export const GET=(req:NextRequest)=>handlers.GET(externalRequest(req));
export const POST=(req:NextRequest)=>handlers.POST(externalRequest(req));
