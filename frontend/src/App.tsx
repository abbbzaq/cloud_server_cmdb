import { Button } from "@/components/ui/button";

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-5xl p-6 md:p-10">
        <header className="rounded-xl border border-border bg-card p-6 md:p-8">
          <p className="text-sm text-muted-foreground">Orion CMDB Frontend</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">React + shadcn/ui</h1>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            前端基础工程已初始化，可在此继续接入路由、状态管理与后端 API。
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button>开始开发</Button>
            <Button variant="secondary">查看文档</Button>
            <Button variant="outline">联调 API</Button>
          </div>
        </header>
      </div>
    </div>
  );
}
