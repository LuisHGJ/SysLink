import type { Dificuldade } from "@/api/types";
import styles from "./DificuldadeBadge.module.css";

const DIFF_CLASS: Record<Dificuldade, string> = {
  Fácil: styles.facil,
  Médio: styles.medio,
  Difícil: styles.dificil,
};

interface Props {
  dificuldade: Dificuldade;
}

export function DificuldadeBadge({ dificuldade }: Props) {
  return <span className={`${styles.badge} ${DIFF_CLASS[dificuldade]}`}>{dificuldade}</span>;
}
