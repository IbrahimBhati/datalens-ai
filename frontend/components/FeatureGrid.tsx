export function FeatureGrid() {
  const features = [
    {
      title: "Data Quality Scoring",
      badge: "Automated",
      description:
        "Deterministic evaluation across completeness, validity, uniqueness, and consistency with a 0-100 grade.",
      icon: (
        <svg className="h-5 w-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      title: "Deep Statistical Profiling",
      badge: "In-depth",
      description:
        "Distribution stats, cardinality analysis, missing value rates, and automated type inference for every column.",
      icon: (
        <svg className="h-5 w-5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
    },
    {
      title: "AI Explanations & Cleaning",
      badge: "Intelligent",
      description:
        "Contextual explanations of root causes, impact assessments, and guided remediation strategies.",
      icon: (
        <svg className="h-5 w-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
    },
  ];

  return (
    <section className="max-w-5xl mx-auto px-4 py-12">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature, idx) => (
          <div
            key={idx}
            className="rounded-2xl border border-white/[0.08] bg-[#161a2e]/50 p-6 backdrop-blur-sm hover:border-white/[0.18] hover:bg-[#161a2e]/80 transition-all duration-200"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.05] border border-white/[0.08]">
                {feature.icon}
              </div>
              <span className="rounded-full bg-white/[0.05] border border-white/[0.08] px-2 py-0.5 text-[11px] font-medium text-slate-300">
                {feature.badge}
              </span>
            </div>
            <h4 className="text-base font-semibold text-white mb-2 tracking-tight">
              {feature.title}
            </h4>
            <p className="text-sm text-slate-400 leading-relaxed">
              {feature.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
