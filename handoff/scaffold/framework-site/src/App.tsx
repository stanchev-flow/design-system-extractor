import { Section, Container } from "@/components/ui/section";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/** Pipeline scaffold — replaced by framework generation (src/App.tsx). */
export function App() {
  return (
    <div className="min-h-screen bg-surface-primary">
      <Section surface="canvas">
        <Container className="flex flex-col items-start gap-4 py-24">
          <Badge>Framework scaffold</Badge>
          <h1 className="text-h1">Design system landing page</h1>
          <p className="text-lead text-text-muted max-w-xl">
            This placeholder is overwritten when framework site generation runs.
          </p>
          <Button withArrow>Get started</Button>
        </Container>
      </Section>
    </div>
  );
}
