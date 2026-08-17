# strona_ai

Strona [ai.ihpan.edu.pl](https://ai.ihpan.edu.pl) zawiera infromacje o pracach związanych z zastosowaniem AI w badaniach historycznych, prowadzonych przez Pracownie Historii Cyfrowej IHPAN.

## Struktura

- `src/pages/` - treść stron i ich metadane,
- `src/pages/pl/` i `src/pages/en/` - polskie i angielskie źródła stron,
- `src/pages/redirects/` - przekierowania ze starszych adresów `.html`,
- `src/_data/seo.json` - opisy i obrazy używane w metadanych SEO,
- `src/_includes/` - wspólny layout, nawigacja i stopka,
- `src/assets/` - arkusze stylów, skrypty i obrazy,
- `src/downloads/` - pliki udostępniane do pobrania,
- `html/` - wygenerowana witryna publikowana na serwerze.

Plików w `html/` nie należy edytować ręcznie. Zmiany należy wprowadzać w `src/`,
a następnie przebudować witrynę.

Publiczne strony używają prefiksów `/pl/` i `/en/`. Jeżeli strona ma
tłumaczenie, oba źródła powinny zawierać wzajemne pola `alternateUrl` oraz
`alternateLang`. Strony bez tłumaczenia pozostają wyłącznie w swoim języku.

## Praca lokalna

Instalacja zależności:

```bash
npm ci
```

Jednorazowe zbudowanie witryny:

```bash
npm run build
```

Serwer deweloperski z automatycznym przebudowywaniem:

```bash
npm run dev
```

Kontrola lokalnych odsyłaczy, dostępności, podstawowych reguł bezpieczeństwa
oraz metadanych SEO w wygenerowanym HTML:

```bash
npm run check
```
