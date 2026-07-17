import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity, ArrowRight, BookOpen, Braces, Check, ChevronRight, CircleDot,
  Cpu, Database, FileCheck2, Fingerprint, GitFork, Hash, LockKeyhole,
  Network, Radio, ShieldCheck, TerminalSquare
} from 'lucide-react';

type Performance = {
  predictions: number;
  accuracy: number;
  symbols: number;
};

const proofChain = [
  ['01', 'Context', 'Capture the prompt, selected context, and declared runtime.'],
  ['02', 'Execution', 'Record commands, outputs, file changes, and model decisions.'],
  ['03', 'Verification', 'Attach tests, hashes, receipts, and explicit truth labels.'],
  ['04', 'Export', 'Package the chain for replay, review, or diligence.'],
];

const surfaces = [
  {
    icon: TerminalSquare,
    title: 'Local agent',
    label: 'OFFLINE-FIRST',
    body: 'A workstation runtime for coding work, local models, commands, diffs, tests, and durable receipts.',
  },
  {
    icon: Fingerprint,
    title: 'Evidence ledger',
    label: 'TAMPER-EVIDENT',
    body: 'Signed work receipts connect an action to its inputs, output, verification state, and provenance.',
  },
  {
    icon: Braces,
    title: 'OverML',
    label: 'EXPERIMENTAL',
    body: 'A deterministic language package for expressing model operations with explicit provenance.',
  },
  {
    icon: Network,
    title: 'Cloud surface',
    label: 'DEMO',
    body: 'A deployable API and dashboard for exploring telemetry, predictions, receipts, and system state.',
  },
];

export default function LandingPage() {
  const [performance, setPerformance] = useState<Performance>({
    predictions: 0,
    accuracy: 0,
    symbols: 0,
  });

  useEffect(() => {
    fetch('/api/performance')
      .then((r) => r.json())
      .then((d) => {
        const stats = d.stats || {};
        setPerformance({
          predictions: stats.total || 0,
          accuracy: Math.round((stats.accuracy || 0) * 100),
          symbols: Object.keys(d.accuracy_by_symbol || {}).length,
        });
      })
      .catch(() => {});
  }, []);

  return (
    <main className="min-h-screen overflow-hidden bg-[#050706] text-[#f3f7f2] selection:bg-emerald-300 selection:text-black">
      <section className="relative border-b border-white/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_72%_20%,rgba(74,222,128,0.12),transparent_30%),radial-gradient(circle_at_18%_70%,rgba(34,211,238,0.07),transparent_28%)]" />
        <div className="absolute inset-0 opacity-[0.07] [background-image:linear-gradient(rgba(255,255,255,.5)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.5)_1px,transparent_1px)] [background-size:48px_48px]" />

        <div className="relative mx-auto grid min-h-[720px] max-w-7xl items-center gap-16 px-6 py-24 lg:grid-cols-[1.08fr_.92fr] lg:px-10">
          <div>
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/[0.06] px-3 py-1.5 font-mono text-[11px] tracking-[0.16em] text-emerald-200">
              <CircleDot className="h-3.5 w-3.5" />
              EXPERIMENTAL · LOCAL-FIRST · OPEN SOURCE
            </div>

            <h1 className="max-w-4xl text-6xl font-semibold leading-[0.92] tracking-[-0.06em] sm:text-7xl lg:text-[96px]">
              AI work you can
              <span className="block text-emerald-300">prove.</span>
            </h1>

            <p className="mt-8 max-w-2xl text-lg leading-8 text-zinc-400 sm:text-xl">
              OverLLM is a reproducible agent runtime that keeps the evidence around an answer:
              context, commands, diffs, tests, telemetry, receipts, and declared limitations.
            </p>

            <div className="mt-10 flex flex-wrap gap-3">
              <Link
                to="/dashboard"
                className="group inline-flex items-center gap-2 rounded-full bg-emerald-300 px-5 py-3 text-sm font-semibold text-[#071008] transition hover:bg-emerald-200"
              >
                Open live system
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                to="/receipts"
                className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.03] px-5 py-3 text-sm font-medium text-zinc-200 transition hover:border-white/30 hover:bg-white/[0.06]"
              >
                <Hash className="h-4 w-4 text-emerald-300" />
                Inspect receipts
              </Link>
              <Link
                to="/docs"
                className="inline-flex items-center gap-2 px-3 py-3 text-sm font-medium text-zinc-400 transition hover:text-white"
              >
                Read the protocol <ChevronRight className="h-4 w-4" />
              </Link>
            </div>

            <p className="mt-7 max-w-xl font-mono text-[11px] leading-5 text-zinc-600">
              RESEARCH SOFTWARE. A receipt records evidence; it does not guarantee correctness,
              production readiness, financial value, or third-party approval.
            </p>
          </div>

          <div className="relative">
            <div className="absolute -inset-8 rounded-full bg-emerald-300/[0.04] blur-3xl" />
            <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[#090c0a]/90 shadow-2xl shadow-black/50">
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                <div className="flex gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-zinc-700" />
                  <span className="h-2.5 w-2.5 rounded-full bg-zinc-700" />
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                </div>
                <span className="font-mono text-[10px] tracking-[0.2em] text-zinc-600">RECEIPT / LATEST</span>
              </div>

              <div className="space-y-6 p-6 sm:p-8">
                <div className="flex items-start justify-between gap-6">
                  <div>
                    <p className="font-mono text-[10px] tracking-[0.18em] text-zinc-600">WORK UNIT</p>
                    <p className="mt-2 text-lg font-medium">landing-page-revision</p>
                  </div>
                  <div className="flex items-center gap-2 rounded-full bg-emerald-300/10 px-3 py-1 font-mono text-[10px] text-emerald-300">
                    <Check className="h-3 w-3" /> VERIFIED
                  </div>
                </div>

                <div className="space-y-3">
                  <ReceiptRow icon={Database} label="context" value="selected + hashed" />
                  <ReceiptRow icon={TerminalSquare} label="command" value="captured" />
                  <ReceiptRow icon={FileCheck2} label="diff" value="1 file changed" />
                  <ReceiptRow icon={ShieldCheck} label="test" value="attached" />
                </div>

                <div className="rounded-2xl border border-white/[0.07] bg-black/30 p-4">
                  <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.15em] text-zinc-600">
                    <LockKeyhole className="h-3.5 w-3.5 text-emerald-300" />
                    SHA-256
                  </div>
                  <p className="mt-3 break-all font-mono text-xs leading-5 text-zinc-400">
                    2c7b8f12e950a941d4e6a8c3...9f03a61be7
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-3 border-t border-white/10 pt-5">
                  <TinyMetric value={performance.predictions || '—'} label="predictions" />
                  <TinyMetric value={performance.accuracy ? `${performance.accuracy}%` : '—'} label="measured accuracy" />
                  <TinyMetric value={performance.symbols || '—'} label="symbols" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-24 lg:px-10">
        <div className="grid gap-12 lg:grid-cols-[.68fr_1.32fr]">
          <div>
            <p className="font-mono text-xs tracking-[0.2em] text-emerald-300">ONE RUNTIME, FOUR SURFACES</p>
            <h2 className="mt-5 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">
              Preserve the work around the model.
            </h2>
            <p className="mt-6 max-w-md leading-7 text-zinc-500">
              Models can be replaced. Evidence should survive. OverLLM treats the surrounding work
              as a protocol instead of disposable chat history.
            </p>
          </div>

          <div className="grid gap-px overflow-hidden rounded-3xl border border-white/10 bg-white/10 sm:grid-cols-2">
            {surfaces.map(({ icon: Icon, title, label, body }) => (
              <article key={title} className="bg-[#080a09] p-7 transition hover:bg-[#0c100d]">
                <div className="flex items-center justify-between">
                  <Icon className="h-5 w-5 text-emerald-300" />
                  <span className="font-mono text-[9px] tracking-[0.16em] text-zinc-600">{label}</span>
                </div>
                <h3 className="mt-8 text-xl font-medium">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-zinc-500">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-white/10 bg-[#080a09]">
        <div className="mx-auto max-w-7xl px-6 py-24 lg:px-10">
          <div className="mb-14 flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
            <div>
              <p className="font-mono text-xs tracking-[0.2em] text-cyan-300">THE DILIGENCE CHAIN</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">From prompt to proof.</h2>
            </div>
            <p className="max-w-md text-sm leading-6 text-zinc-500">
              Each stage produces a reviewable artifact. Missing evidence remains visible instead of
              being converted into confidence.
            </p>
          </div>

          <div className="grid gap-px overflow-hidden rounded-3xl border border-white/10 bg-white/10 lg:grid-cols-4">
            {proofChain.map(([number, title, body]) => (
              <article key={number} className="relative bg-[#060807] p-7">
                <span className="font-mono text-xs text-emerald-300">{number}</span>
                <h3 className="mt-12 text-xl font-medium">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-zinc-500">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-10 px-6 py-24 lg:grid-cols-2 lg:px-10">
        <div className="rounded-3xl border border-white/10 bg-[linear-gradient(145deg,rgba(74,222,128,.08),transparent_55%)] p-8 sm:p-10">
          <Radio className="h-6 w-6 text-emerald-300" />
          <h2 className="mt-10 text-3xl font-semibold tracking-[-0.03em]">See what is actually running.</h2>
          <p className="mt-4 max-w-lg leading-7 text-zinc-500">
            The dashboard exposes current telemetry, prediction performance, system activity, and
            available receipts. Empty states stay empty; unavailable evidence is not simulated.
          </p>
          <Link to="/dashboard" className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-emerald-300 hover:text-emerald-200">
            Open dashboard <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="rounded-3xl border border-white/10 bg-[linear-gradient(145deg,rgba(34,211,238,.07),transparent_55%)] p-8 sm:p-10">
          <GitFork className="h-6 w-6 text-cyan-300" />
          <h2 className="mt-10 text-3xl font-semibold tracking-[-0.03em]">Fork the protocol, not the claims.</h2>
          <p className="mt-4 max-w-lg leading-7 text-zinc-500">
            URAP-1 gives adopters a reproducible starting point: declare the fork, record the commit,
            preserve truth labels, and publish only what the evidence supports.
          </p>
          <Link to="/docs" className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-cyan-300 hover:text-cyan-200">
            Read documentation <BookOpen className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-5 px-6 py-8 text-xs text-zinc-600 sm:flex-row sm:items-center lg:px-10">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-300" />
            <span className="font-medium text-zinc-400">OverLLM</span>
            <span>Reproducible agent runtime</span>
          </div>
          <span className="font-mono">EXPERIMENTAL RESEARCH SOFTWARE · VERIFY BEFORE RELYING</span>
        </div>
      </footer>
    </main>
  );
}

function ReceiptRow({ icon: Icon, label, value }: { icon: typeof Database; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.025] px-4 py-3">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-zinc-600" />
        <span className="font-mono text-xs text-zinc-500">{label}</span>
      </div>
      <span className="font-mono text-[11px] text-zinc-300">{value}</span>
    </div>
  );
}

function TinyMetric({ value, label }: { value: string | number; label: string }) {
  return (
    <div>
      <div className="font-mono text-lg text-zinc-200">{value}</div>
      <div className="mt-1 text-[10px] leading-4 text-zinc-600">{label}</div>
    </div>
  );
}
