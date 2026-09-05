import { STATUS_COLOR, STATUS_LABEL, type Status } from "../lib/types";

export default function StatusPill({ status }: { status: Status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs ${STATUS_COLOR[status]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATUS_LABEL[status]}
    </span>
  );
}
