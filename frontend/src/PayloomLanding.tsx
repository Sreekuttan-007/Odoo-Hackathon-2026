import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, Fingerprint, Sparkles, UserRound } from "lucide-react";
import "./payloom-landing.css";

export type PayloomLandingProps = {
  onSubmit?: (email: string, password: string) => Promise<void> | void;
  defaultEmail?: string;
  defaultPassword?: string;
  demoMode?: boolean;
};

function PayloomMark() {
  return <div className="pl-mark-wrap"><div className="pl-mark" aria-hidden="true"><i/><i/><i/><i/></div><span>payloom</span></div>;
}

export default function PayloomLanding({
  onSubmit,
  defaultEmail = "",
  defaultPassword = "",
  demoMode = false,
}: PayloomLandingProps) {
  const [email, setEmail] = useState(defaultEmail);
  const [password, setPassword] = useState(defaultPassword);
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSubmit?.(email, password);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sign in failed. Check your credentials and try again.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="pl-page">
    <section className="pl-brand-stage">
      <div className="pl-grid"/><div className="pl-ambient pl-a1"/><div className="pl-ambient pl-a2"/>
      <div className="pl-stage-top"><PayloomMark/><span className="pl-system-state"><i/> SYSTEM OPERATIONAL</span></div>
      <div className="pl-weave" aria-hidden="true">
        <svg viewBox="0 0 900 520" preserveAspectRatio="none">
          <path className="pl-thread pl-t1" d="M-20 110 C170 110 180 400 420 275 S650 95 930 130"/>
          <path className="pl-thread pl-t2" d="M-20 395 C210 390 220 145 445 260 S680 410 930 365"/>
          <path className="pl-thread pl-t3" d="M-20 230 C185 225 245 315 440 265 S690 205 930 240"/>
          <path className="pl-thread pl-t4" d="M-20 290 C195 305 255 205 450 270 S690 310 930 285"/>
        </svg>
        <span className="pl-node pl-n1"/><span className="pl-node pl-n2"/><span className="pl-node pl-n3"/>
      </div>
      <div className="pl-brand-copy"><span className="pl-eyebrow">THE OPERATING SYSTEM FOR PEOPLE</span><h1>Every person.<br/>Every payment.<br/><em>Perfectly aligned.</em></h1><p>HR and payroll, woven into one precise flow—from first day to payday.</p></div>
      <div className="pl-stage-foot"><span>256-bit encryption</span><span>Role-based access</span><span>Audit-ready</span></div>
    </section>
    <section className="pl-login-panel">
      <div className="pl-mobile-brand"><PayloomMark/></div>
      <form onSubmit={submit} className="pl-login-card">
        <div className="pl-welcome-icon"><Fingerprint size={24}/></div>
        <p className="pl-eyebrow">SECURE WORKSPACE</p><h2>Welcome back</h2><p className="pl-subcopy">Enter your work credentials to continue.</p>
        <label>Work email<div className="pl-input"><input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required/><UserRound size={17}/></div></label>
        <label>Password<div className="pl-input"><input type={showPassword?"text":"password"} autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/><button type="button" onClick={()=>setShowPassword(value=>!value)} aria-label={showPassword?"Hide password":"Show password"}>{showPassword?<EyeOff size={17}/>:<Eye size={17}/>}</button></div></label>
        {error&&<div className="pl-error" role="alert">{error}</div>}
        <button className="pl-submit" disabled={busy}>{busy?<span className="pl-loader"/>:<>Sign in to Payloom <ArrowRight size={17}/></>}</button>
        {demoMode&&<div className="pl-demo"><Sparkles size={15}/><span><strong>Demo workspace</strong><br/>Credentials are prefilled for review.</span></div>}
      </form>
      <footer>Protected by Payloom Secure Access · v1.0</footer>
    </section>
  </main>;
}
