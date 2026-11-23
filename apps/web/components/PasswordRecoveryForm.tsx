'use client';
import React,{useEffect,useState,useRef} from 'react';
import Link from 'next/link';
import {signOut} from 'next-auth/react';
import {api} from '@/lib/api';
export default function PasswordRecoveryForm({reset=false}:{reset?:boolean}){
 const[email,setEmail]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[token,setToken]=useState('');
 const tokenCaptured=useRef(false);
 const[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[done,setDone]=useState(false);
 useEffect(()=>{if(reset&&!tokenCaptured.current){tokenCaptured.current=true;const params=new URLSearchParams(window.location.hash.slice(1));setToken(params.get('token')||'');window.history.replaceState(null,'',window.location.pathname);}},[reset]);
 async function submit(e:React.FormEvent){
  e.preventDefault();if(busy)return;setError('');
  if(reset&&(!token||password.length<8||password.length>128||password!==confirm)){setError(!token?'This reset link is missing its token. Request a new link.':'Use 8 to 128 characters and matching passwords.');return;}
  setBusy(true);
  try{
   const response=await api.post(reset?'/auth/password-reset/confirm':'/auth/password-reset/request',reset?{token,password}:{email:email.trim()});
   setMessage(response.data.message);setDone(true);
   if(reset){setToken('');setPassword('');setConfirm('');await signOut({redirect:false});}
  }catch(e:any){setError(e?.response?.status===429?'Too many attempts. Wait a few minutes before trying again.':e?.response?.status===400?'This reset link is invalid or expired. Request a new link.':'Password recovery is temporarily unavailable. Please try again later.');}
  finally{setBusy(false);}
 }
 const inputClass='w-full rounded-full bg-zinc-900/90 border border-white/15 py-3.5 px-5 text-white outline-none focus:border-cyan-300 disabled:opacity-50';
 return <section className="relative min-h-[85svh] flex items-center justify-center px-5 py-32 bg-[#050505] text-white">
  <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,0.12),transparent_65%)] pointer-events-none"/>
  <div className="relative w-full max-w-md text-center space-y-6">
   <h1 className="text-3xl sm:text-4xl uppercase font-black tracking-tighter" style={{fontFamily:"'Orbitron',sans-serif"}}>{reset?'Choose a new password':'Forgot your password?'}</h1>
   <p className="text-sm text-zinc-400">{reset?'A new password signs out your other sessions.':'Enter your account email. If it is eligible, we will send a one-time reset link.'}</p>
   {done?<p role="status" className="rounded-3xl border border-cyan-200/20 bg-cyan-200/5 p-5 text-sm leading-relaxed">{message}</p>:<form onSubmit={submit} className="space-y-4 text-left">
    {reset?<>
     <label className="block text-xs text-zinc-300 space-y-2"><span>New password</span><input aria-label="New password" className={inputClass} type="password" autoComplete="new-password" minLength={8} maxLength={128} required disabled={busy} value={password} onChange={e=>setPassword(e.target.value)}/></label>
     <label className="block text-xs text-zinc-300 space-y-2"><span>Confirm new password</span><input aria-label="Confirm new password" className={inputClass} type="password" autoComplete="new-password" minLength={8} maxLength={128} required disabled={busy} value={confirm} onChange={e=>setConfirm(e.target.value)}/></label>
    </>:<label className="block text-xs text-zinc-300 space-y-2"><span>Email address</span><input aria-label="Email address" className={inputClass} type="email" autoComplete="email" maxLength={254} required disabled={busy} value={email} onChange={e=>setEmail(e.target.value)}/></label>}
    {error&&<p role="alert" className="text-sm text-rose-300 px-2">{error}</p>}
    <button disabled={busy} className="w-full rounded-full py-3.5 bg-white text-black font-semibold text-sm disabled:opacity-50">{busy?'Please wait...':reset?'Update password':'Send reset link'}</button>
   </form>}
   <div className="flex flex-col gap-3 text-sm"><Link href="/login" className="text-white hover:text-cyan-200">Back to sign in</Link>{reset&&<Link href="/forgot-password" className="text-zinc-400 hover:text-white">Request a new reset link</Link>}</div>
  </div>
 </section>;
}
