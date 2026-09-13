# BH Process Studio

Local browser PFD editor for the BH simulator. It is deliberately separated from the scientific kernel: this package edits typed case data, calls the versioned simulation API, and displays returned results. It contains no engineering equations.

## Development

```sh
npm install
npm run dev
```

Vite serves the interface at `http://localhost:4173` and proxies `/api` to `http://127.0.0.1:8000`.

## Verification

```sh
npm run test
npm run build
npm run lint
```

## API contract

The client targets `/api/v1alpha` and expects `{ "apiVersion": "v1alpha", "data": ... }` envelopes. It currently calls:

- `PUT /drafts/{draftId}` to save a revision.
- `POST /drafts/{draftId}/validate` to validate a revision.
- `POST /drafts/{draftId}/runs` to create an immutable run.

The PFD performs a small topology preflight before sending a request, but server validation and the scientific kernel remain authoritative. A service failure is visible and does not fabricate a run result.
