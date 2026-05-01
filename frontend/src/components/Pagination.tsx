export function Pagination({
  page,
  total,
  limit = 10,
  onChange,
}: {
  page: number;
  total: number;
  limit?: number;
  onChange: (page: number) => void;
}) {
  const lastPage = Math.max(0, Math.ceil(total / limit) - 1);

  return (
    <div className="pagination">
      <button type="button" onClick={() => onChange(Math.max(0, page - 1))} disabled={page === 0}>
        Anterior
      </button>
      <span>
        Página {page + 1} de {lastPage + 1}
      </span>
      <button type="button" onClick={() => onChange(Math.min(lastPage, page + 1))} disabled={page >= lastPage}>
        Próxima
      </button>
    </div>
  );
}
