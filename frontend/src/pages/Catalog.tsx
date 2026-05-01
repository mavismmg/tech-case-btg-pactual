import { FormEvent, useState } from "react";

import { authorApi, bookApi, requestApi } from "../api/resources";
import type { Account, Book } from "../api/types";
import { Pagination } from "../components/Pagination";
import { Panel } from "../components/Panel";
import { Badge, EmptyState, Notice } from "../components/Status";
import { errorMessage, useAsync } from "../hooks";
import { formatBookAvailability, formatDate } from "../utils/formatters";

export function CatalogPage({ account }: { account: Account }) {
  const isStaff = account.role === "admin" || account.role === "librarian";
  const [page, setPage] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authorName, setAuthorName] = useState("");
  const [bookPayload, setBookPayload] = useState({ title: "", isbn: "", author_id: "", published_date: "2024-01-01" });
  const [isbnSearch, setIsbnSearch] = useState("");
  const [exemplars, setExemplars] = useState<Book[]>([]);
  const [savingAuthor, setSavingAuthor] = useState(false);
  const [savingBook, setSavingBook] = useState(false);
  const [searchingIsbn, setSearchingIsbn] = useState(false);
  const [requestingBookId, setRequestingBookId] = useState<number | null>(null);
  const authors = useAsync(() => authorApi.list(0), [], "load");
  const books = useAsync(() => bookApi.list(page), [page], "load");

  async function createAuthor(event: FormEvent) {
    event.preventDefault();
    const trimmedName = authorName.trim();

    if (!trimmedName) {
      setError("Informe o nome do autor.");
      return;
    }

    setError(null);
    setMessage(null);
    setSavingAuthor(true);
    try {
      await authorApi.create({ name: trimmedName });
      setAuthorName("");
      setMessage("Autor cadastrado com sucesso.");
      authors.reload();
    } catch (err) {
      setError(errorMessage(err, "createAuthor"));
    } finally {
      setSavingAuthor(false);
    }
  }

  async function createBook(event: FormEvent) {
    event.preventDefault();
    const title = bookPayload.title.trim();
    const isbn = bookPayload.isbn.trim();

    if (!title) {
      setError("Informe o título do livro.");
      return;
    }

    if (!isbn) {
      setError("Informe o ISBN do livro.");
      return;
    }

    if (!bookPayload.author_id) {
      setError("Selecione o autor do livro.");
      return;
    }

    setError(null);
    setMessage(null);
    setSavingBook(true);
    try {
      await bookApi.create({ ...bookPayload, title, isbn, author_id: Number(bookPayload.author_id) });
      setBookPayload({ title: "", isbn: "", author_id: "", published_date: "2024-01-01" });
      setMessage("Livro cadastrado com sucesso.");
      books.reload();
    } catch (err) {
      setError(errorMessage(err, "createBook"));
    } finally {
      setSavingBook(false);
    }
  }

  async function searchIsbn(event: FormEvent) {
    event.preventDefault();
    const isbn = isbnSearch.trim();
    if (!isbn) {
      setError("Informe o ISBN para consultar a disponibilidade.");
      return;
    }

    setError(null);
    setMessage(null);
    setSearchingIsbn(true);
    try {
      const count = await bookApi.count(isbn);
      const list = await bookApi.exemplars(isbn);
      setMessage(
        count.is_available
          ? `${count.available_exemplars} exemplar(es) disponível(is) para empréstimo.`
          : "Não há exemplares disponíveis para empréstimo no momento.",
      );
      setExemplars(list);
    } catch (err) {
      setError(errorMessage(err, "searchIsbn"));
      setExemplars([]);
    } finally {
      setSearchingIsbn(false);
    }
  }

  async function requestLoan(bookId: number) {
    setError(null);
    setMessage(null);
    setRequestingBookId(bookId);
    try {
      await requestApi.createLoan(bookId);
      setMessage("Solicitação de empréstimo enviada. Acompanhe o andamento em Meu Espaço.");
    } catch (err) {
      setError(errorMessage(err, "requestLoan"));
    } finally {
      setRequestingBookId(null);
    }
  }

  return (
    <div className="page">
      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}

      <div className="two-columns-grid">
        {isStaff ? (
          <Panel title="Cadastro do catálogo">
            <form className="form-grid" onSubmit={createAuthor}>
              <label>
                Novo autor
                <input value={authorName} onChange={(event) => setAuthorName(event.target.value)} placeholder="Ex.: Machado de Assis" required />
              </label>
              <button disabled={savingAuthor}>{savingAuthor ? "Criando..." : "Criar autor"}</button>
            </form>
            <form className="form-grid" onSubmit={createBook}>
              <label>
                Título
                <input
                  value={bookPayload.title}
                  onChange={(event) => setBookPayload({ ...bookPayload, title: event.target.value })}
                  placeholder="Título que aparecerá no catálogo"
                  required
                />
              </label>
              <label>
                ISBN
                <input
                  value={bookPayload.isbn}
                  onChange={(event) => setBookPayload({ ...bookPayload, isbn: event.target.value })}
                  placeholder="Ex.: 9788535914849"
                  required
                />
              </label>
              <label>
                Autor
                <select value={bookPayload.author_id} onChange={(event) => setBookPayload({ ...bookPayload, author_id: event.target.value })} required>
                  <option value="">{authors.loading ? "Carregando autores..." : "Selecione um autor"}</option>
                  {authors.data?.items.map((author) => (
                    <option key={author.id} value={author.id}>
                      {author.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Publicação
                <input
                  type="date"
                  value={bookPayload.published_date}
                  onChange={(event) => setBookPayload({ ...bookPayload, published_date: event.target.value })}
                  required
                />
              </label>
              <button className="primary" disabled={savingBook || authors.loading}>
                {savingBook ? "Criando..." : "Criar livro"}
              </button>
            </form>
          </Panel>
        ) : null}

        <Panel title="Disponibilidade por ISBN">
          <form className="inline-form" onSubmit={searchIsbn}>
            <label>
              ISBN
              <input value={isbnSearch} onChange={(event) => setIsbnSearch(event.target.value)} placeholder="Digite o ISBN" required />
            </label>
            <button disabled={searchingIsbn}>{searchingIsbn ? "Consultando..." : "Consultar"}</button>
          </form>
          <div className="chips">
            {exemplars.map((book) => (
              <Badge key={book.id} tone={book.is_available ? "good" : "warn"}>
                #{book.id} {formatBookAvailability(book.is_available)}
              </Badge>
            ))}
          </div>
          {!exemplars.length && !searchingIsbn ? <EmptyState title="Consulte um ISBN" detail="Os exemplares encontrados aparecerão aqui." /> : null}
        </Panel>
      </div>

      <Panel title="Livros">
        {books.error ? <Notice tone="error">{books.error}</Notice> : null}
        {books.loading ? <EmptyState title="Carregando livros..." detail="Buscando catálogo disponível." /> : null}
        {books.data?.items.length ? (
          <>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Título</th>
                  <th>Autor</th>
                  <th>ISBN</th>
                  <th>Publicação</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {books.data.items.map((book) => (
                  <tr key={book.id}>
                    <td>{book.id}</td>
                    <td>{book.title}</td>
                    <td>{book.author?.name ?? book.author_id}</td>
                    <td>{book.isbn}</td>
                    <td>{formatDate(book.published_date)}</td>
                    <td>
                      <Badge tone={book.is_available ? "good" : "warn"}>{formatBookAvailability(book.is_available)}</Badge>
                    </td>
                    <td>
                      {!isStaff && book.is_available ? (
                        <button onClick={() => requestLoan(book.id)} disabled={requestingBookId === book.id}>
                          {requestingBookId === book.id ? "Solicitando..." : "Solicitar"}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} total={books.data.total} onChange={setPage} />
          </>
        ) : (
          !books.loading && <EmptyState title="Nenhum livro encontrado" detail="Cadastre livros para começar a montar o catálogo." />
        )}
      </Panel>
    </div>
  );
}
