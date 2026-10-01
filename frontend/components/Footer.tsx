export function Footer() {
  return (
    <footer className="mt-auto w-full border-t border-white/[0.08] py-8 text-center text-xs text-slate-500">
      <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-400">DataLens AI</span>
          <span>— Production Dataset Quality Analyzer</span>
        </div>
        <div className="flex items-center gap-6">
          <span className="hover:text-slate-400 transition-colors">FastAPI Backend</span>
          <span className="hover:text-slate-400 transition-colors">Next.js Frontend</span>
          <span className="hover:text-slate-400 transition-colors">TypeScript</span>
        </div>
      </div>
    </footer>
  );
}
