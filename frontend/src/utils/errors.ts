import { ApiError } from "../api/client";

export type ErrorContext =
  | "login"
  | "load"
  | "createUser"
  | "loadUserLoans"
  | "createAuthor"
  | "createBook"
  | "searchIsbn"
  | "requestLoan"
  | "createLoan"
  | "returnLoan"
  | "requestAction"
  | "approveRequest"
  | "rejectRequest"
  | "notifications";

const contextFallbacks: Partial<Record<ErrorContext, string>> = {
  login: "Não foi possível entrar. Confira seu email e senha.",
  load: "Não foi possível carregar os dados. Tente novamente.",
  createUser: "Não foi possível cadastrar o usuário. Verifique os dados e tente novamente.",
  loadUserLoans: "Não foi possível carregar os empréstimos desse usuário.",
  createAuthor: "Não foi possível cadastrar o autor. Verifique o nome e tente novamente.",
  createBook: "Não foi possível cadastrar o livro. Verifique os dados e tente novamente.",
  searchIsbn: "Não foi possível consultar esse ISBN. Verifique o código informado.",
  requestLoan: "Não foi possível solicitar o empréstimo desse livro.",
  createLoan: "Não foi possível realizar o empréstimo agora. Tente novamente em instantes.",
  returnLoan: "Não foi possível devolver este empréstimo agora.",
  requestAction: "Não foi possível enviar sua solicitação. Verifique o empréstimo informado.",
  approveRequest: "Não foi possível aprovar a solicitação.",
  rejectRequest: "Não foi possível rejeitar a solicitação.",
  notifications: "Não foi possível enviar as notificações agora.",
};

const validationFallbacks: Partial<Record<ErrorContext, string>> = {
  createUser: "Preencha nome e email corretamente para cadastrar o usuário.",
  createAuthor: "Informe o nome do autor para continuar.",
  createBook: "Preencha título, ISBN, autor e data de publicação para cadastrar o livro.",
  createLoan: "Informe IDs válidos de usuário e livro para realizar o empréstimo.",
  requestAction: "Informe um ID de empréstimo válido.",
  notifications: "Informe uma quantidade de dias entre 0 e 30.",
};

function isConnectionError(err: unknown) {
  return err instanceof TypeError || (err instanceof Error && /failed to fetch|network|fetch/i.test(err.message));
}

function normalizeDetail(detail: string) {
  return detail.toLowerCase();
}

function messageFromDetail(detail: string, context?: ErrorContext) {
  const normalized = normalizeDetail(detail);

  if (normalized.includes("already has 3 active loans")) {
    return "O usuário já atingiu o limite de 3 empréstimos ativos.";
  }

  if (normalized.includes("book is not available")) {
    return "Este livro não está disponível para empréstimo no momento.";
  }

  if (normalized.includes("user with email") && normalized.includes("already exists")) {
    return "Já existe um usuário cadastrado com este email.";
  }

  if (normalized.includes("author") && normalized.includes("already exists")) {
    return "Já existe um autor cadastrado com esse nome.";
  }

  if (normalized.includes("title already exists") || normalized.includes("different isbn")) {
    return "Já existe um livro desse autor com o mesmo título e outro ISBN.";
  }

  if (normalized.includes("pending request already exists")) {
    return "Já existe uma solicitação pendente para esta operação.";
  }

  if (normalized.includes("already been reviewed")) {
    return "Essa solicitação já foi analisada.";
  }

  if (normalized.includes("already been returned")) {
    return "Este empréstimo já foi devolvido.";
  }

  if (normalized.includes("loan does not belong")) {
    return "Esse empréstimo não pertence ao leitor autenticado.";
  }

  if (normalized.includes("loan must be active")) {
    return "Apenas empréstimos em andamento podem receber essa solicitação.";
  }

  if (normalized.includes("renewal limit reached")) {
    return "Este empréstimo já atingiu o limite de renovações.";
  }

  if (normalized.includes("loan is overdue")) {
    return "Empréstimos atrasados não podem ser renovados.";
  }

  if (normalized.includes("invalid credentials")) {
    return "Email ou senha incorretos.";
  }

  if (normalized.includes("inactive account")) {
    return "Esta conta está inativa. Fale com a biblioteca.";
  }

  if (normalized.includes("user") && normalized.includes("not found")) {
    return "Não encontramos esse usuário. Verifique o ID informado.";
  }

  if (normalized.includes("user") && normalized.includes("does not exist")) {
    return "Não encontramos esse usuário. Verifique o ID informado.";
  }

  if (normalized.includes("book") && normalized.includes("not found")) {
    return "Não encontramos esse livro. Verifique o ID informado.";
  }

  if (normalized.includes("book") && (normalized.includes("does not exist") || normalized.includes("do not exist"))) {
    return "Não encontramos esse livro. Verifique o ID informado.";
  }

  if (normalized.includes("author") && normalized.includes("not found")) {
    return "Não encontramos esse autor. Verifique a seleção informada.";
  }

  if (normalized.includes("loan request") && normalized.includes("not found")) {
    return "Não encontramos essa solicitação.";
  }

  if (normalized.includes("loan") && normalized.includes("not found")) {
    return "Não encontramos esse empréstimo. Verifique o ID informado.";
  }

  if (normalized.includes("internal server error") || normalized.includes("unexpected error") || normalized.includes("an error occurred")) {
    return contextFallbacks[context ?? "load"] ?? "Não foi possível concluir a operação agora. Tente novamente em instantes.";
  }

  return null;
}

export function getUserFriendlyErrorMessage(err: unknown, context?: ErrorContext) {
  if (isConnectionError(err)) {
    return "Não foi possível conectar ao serviço da biblioteca. Tente novamente em instantes.";
  }

  if (err instanceof ApiError) {
    if (err.status === 401) return context === "login" ? "Email ou senha incorretos." : "Sessão inválida. Faça login novamente.";
    if (err.status === 403) return "Você não tem permissão para realizar esta ação.";
    if (err.status === 422) return validationFallbacks[context ?? "load"] ?? "Revise os dados informados e tente novamente.";

    const detailMessage = messageFromDetail(err.detail, context);
    if (detailMessage) return detailMessage;

    if (err.status >= 500) {
      return contextFallbacks[context ?? "load"] ?? "Não foi possível concluir a operação agora. Tente novamente em instantes.";
    }

    return contextFallbacks[context ?? "load"] ?? "Não foi possível concluir a operação. Verifique os dados e tente novamente.";
  }

  return contextFallbacks[context ?? "load"] ?? "Erro inesperado. Tente novamente.";
}
