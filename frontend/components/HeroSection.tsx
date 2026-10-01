export function HeroSection() {
  return (
    <section className="text-center pt-12 pb-6 max-w-3xl mx-auto px-4">
      {/* Badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-xs font-medium mb-6 backdrop-blur-sm">
        <span className="flex h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
        Production-Ready Dataset Profiler & Quality Engine
      </div>

      {/* Headline */}
      <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight sm:leading-none">
        Automated Dataset Quality,{" "}
        <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-indigo-200 bg-clip-text text-transparent">
          Explainable & Instant
        </span>
      </h1>

      {/* Description */}
      <p className="mt-5 text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto">
        DataLens AI evaluates tabular datasets for missingness, anomalies, schema drift, and data hygiene. Get transparent quality scoring and AI-powered recommendations before training machine learning models.
      </p>

      {/* Feature tags */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2 sm:gap-3 text-xs text-slate-400 font-mono">
        <span className="rounded-md border border-white/[0.08] bg-white/[0.03] px-2.5 py-1">
          CSV & JSON
        </span>
        <span className="rounded-md border border-white/[0.08] bg-white/[0.03] px-2.5 py-1">
          Up to 50MB
        </span>
        <span className="rounded-md border border-white/[0.08] bg-white/[0.03] px-2.5 py-1">
          Statistical Profiling
        </span>
        <span className="rounded-md border border-white/[0.08] bg-white/[0.03] px-2.5 py-1">
          AI Recommendations
        </span>
      </div>
    </section>
  );
}
