import type { Role } from "../api/types";

export function formatCurrency(value?: number | null) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value ?? 0);
}

export function formatDate(value?: string | null) {
  if (!value) return "Não informado";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data inválida";

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: value.includes("T") ? "short" : undefined,
  }).format(date);
}

export function formatLoanStatus(status: string) {
  const labels: Record<string, string> = {
    active: "Em andamento",
    returned: "Devolvido",
    overdue: "Atrasado",
  };

  return labels[status] ?? status;
}

export function formatRequestStatus(status: string) {
  const labels: Record<string, string> = {
    pending: "Pendente",
    approved: "Aprovada",
    rejected: "Rejeitada",
  };

  return labels[status] ?? status;
}

export function formatRequestType(type: string) {
  const labels: Record<string, string> = {
    loan: "Empréstimo",
    return: "Devolução",
    renewal: "Renovação",
  };

  return labels[type] ?? type;
}

export function formatRole(role: Role | string) {
  const labels: Record<string, string> = {
    admin: "Administrador",
    librarian: "Bibliotecário",
    reader: "Leitor",
  };

  return labels[role] ?? role;
}

export function formatBookAvailability(isAvailable: boolean) {
  return isAvailable ? "Disponível para empréstimo" : "Indisponível no momento";
}

export function formatOperation(operation: string) {
  const normalized = operation.toLowerCase();
  const labels: Record<string, string> = {
    loan_created: "Empréstimo criado",
    loan_returned: "Empréstimo devolvido",
    loan_renewed: "Empréstimo renovado",
    loan_request_created: "Solicitação criada",
    loan_request_approved: "Solicitação aprovada",
    loan_request_rejected: "Solicitação rejeitada",
  };

  return labels[normalized] ?? operation.replace(/_/g, " ");
}

export function formatNotificationChannel(channel: string) {
  const labels: Record<string, string> = {
    all: "Todos os canais",
    email: "Email",
    webhook: "Canal interno",
  };

  return labels[channel] ?? channel;
}

export function formatDeliveryStatus(status: string, skipped?: boolean) {
  if (skipped) return "Já enviado";

  const labels: Record<string, string> = {
    sent: "Enviado",
    failed: "Falhou",
    skipped: "Já enviado",
  };

  return labels[status] ?? status;
}
