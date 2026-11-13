import type { Status } from "@/api/types";
import styles from "./StatusBadge.module.css";

const STATUS_CLASS: Record<Status, string> = {
  "Não contatado": styles.naoContatado,
  "Aguardando resposta": styles.aguardando,
  Negociando: styles.negociando,
  Negado: styles.negado,
  Fechado: styles.fechado,
  "Em desenvolvimento": styles.emDev,
  Finalizado: styles.finalizado,
};

interface Props {
  status: Status;
}

export function StatusBadge({ status }: Props) {
  return <span className={`${styles.badge} ${STATUS_CLASS[status]}`}>{status}</span>;
}
