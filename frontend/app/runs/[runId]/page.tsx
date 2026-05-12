import RunReport from "../../components/report/RunReport";

export default async function RunDetailPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <RunReport runId={runId} />;
}
