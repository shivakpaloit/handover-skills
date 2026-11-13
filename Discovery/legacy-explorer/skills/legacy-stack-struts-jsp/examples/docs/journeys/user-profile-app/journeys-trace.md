# Journey trace — user-profile-app

Sources: user-profile-app/ (Struts 1.3 + JSP; FE and BE in one codebase) · transcript: none · screenshots: none · test cases: none
Scope: whole app. Plain-language version: [journeys.md](journeys.md).

## Identity and personas

| ID | Claim | Evidence | Status |
|---|---|---|---|
| APP-01 | App "Customer Profile Lookup": search by mobile or email, view one profile. | user-profile-app/WebContent/WEB-INF/web.xml:7, user-profile-app/src/ApplicationResources.properties:1-5, user-profile-app/WebContent/WEB-INF/struts-config.xml:24-46 | Confirmed |
| APP-02 | Search and get call middleware /profile/v1/search and /profile/v1/get, channel CSPORTAL. | user-profile-app/src/middleware.properties:1-3, user-profile-app/src/com/acme/profile/integration/MiddlewareClient.java:30-52 | Confirmed |
| APP-03 | SEARCH and VIEW written to PROFILE_AUDIT via JNDI jdbc/ProfileDS. | user-profile-app/src/com/acme/profile/dao/AuditDao.java:16-30, user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:38, user-profile-app/src/com/acme/profile/web/ProfileAction.java:43 | Confirmed |
| APP-04 | Session attribute staffUser is read but never set here; /login.jsp referenced but absent. | user-profile-app/src/com/acme/profile/web/AuthFilter.java:28-31, user-profile-app/WebContent/WEB-INF/struts-config.xml:19 | Confirmed |
| APP-05 | Users are customer-service staff (CSPORTAL, StaffUser). | user-profile-app/src/middleware.properties:3, user-profile-app/src/com/acme/profile/model/StaffUser.java:7-23 | Inferred (naming) |
| PER-01 | Profile viewer: role PROFILE_VIEWER. | user-profile-app/src/com/acme/profile/web/AuthFilter.java:33 | Confirmed |
| PER-02 | Profile admin: role PROFILE_ADMIN, sees full NRIC. | user-profile-app/src/com/acme/profile/web/AuthFilter.java:33, user-profile-app/src/com/acme/profile/web/ProfileAction.java:39-41 | Confirmed |
| PER-03 | Staff with neither role: 403. | user-profile-app/src/com/acme/profile/web/AuthFilter.java:33-35 | Confirmed |

## J1 · Find a customer

| # | User action | Application component | API | Data exchanged | Logic performed | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 1 | Opens the app | `index.jsp` → ForwardAction → `search.jsp`, `header.jsp` | `GET /` → 302 `GET /showSearch.do` | out: search form, "Signed in as <staffId>" | Access gate (`SEC`, J4); `html:javascript` client validation (`FE`) | user-profile-app/WebContent/WEB-INF/web.xml:54-56, user-profile-app/WebContent/index.jsp:2, user-profile-app/WebContent/WEB-INF/struts-config.xml:24-26, user-profile-app/WebContent/jsp/profile/search.jsp:7, user-profile-app/WebContent/jsp/common/header.jsp:5-6 | Confirmed |
| 2 | Enters mobile or email, optionally ticks include inactive, clicks Search | `search.jsp`, `ProfileSearchForm` (session), `ProfileSearchAction` | form post → `/searchProfiles.do`; outbound POST `mw.endpoint.search` | in: `msisdn`, `email`, `includeInactive`; out: profile list; state: form kept in session | Mobile maxlength 8 (`FE`); mask `^[89][0-9]{7}$` (`FE+BE`); email format, max 80 (`FE+BE`); exactly one criterion (`BE`); trim, email lower-cased (`BE`); drop non-ACTIVE unless ticked (`BE`); cap 20 (`BE`); audit SEARCH (`DATA`), failure ignored | user-profile-app/WebContent/jsp/profile/search.jsp:17-33, user-profile-app/WebContent/WEB-INF/validation.xml:9-23, user-profile-app/WebContent/WEB-INF/struts-config.xml:28-37, user-profile-app/src/com/acme/profile/web/ProfileSearchForm.java:25-38, user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:33-38, user-profile-app/src/com/acme/profile/integration/MiddlewareClient.java:30-43, user-profile-app/src/com/acme/profile/service/ProfileService.java:34-47, user-profile-app/src/com/acme/profile/dao/AuditDao.java:20-33 | Confirmed |
| 3 | Sees the list of matches | `results.jsp` | — | out: Name (link), Mobile (first 4 + XXXX), Email, Status; truncated banner | Banner when results ≥ 20 (`BE`); mobile mask in scriptlet (`FE`) | user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:54-56, user-profile-app/WebContent/jsp/profile/results.jsp:10-27, user-profile-app/src/ApplicationResources.properties:21 | Confirmed |
| 4 | Clicks a name | `results.jsp` `html:link` | `GET /profile.do?method=view&userId=<id>` | in: `userId` | Continues in J2 | user-profile-app/WebContent/jsp/profile/results.jsp:19-21 | Confirmed |

Exits

| From step | Exit | Trigger | User sees | Goes to | Evidence |
|---|---|---|---|---|---|
| 2 | Client validation | Format/length fails | Validator JS alert | step 2 | Inferred (standard `html:javascript`) |
| 2 | Server validation | Both blank / both filled / mask / email | Message on search.jsp | step 2 | user-profile-app/src/com/acme/profile/web/ProfileSearchForm.java:32-37, user-profile-app/src/ApplicationResources.properties:12-17 |
| 2 | No match | 0 after filter, or MW status 1001 | "No matching profiles." | step 2 | user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:40-45 |
| 2 | Single match | 1 profile | Redirect to profile | J2 step 1 | user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:47-52 |
| 2 | System error | MW HTTP ≠ 200, timeout (5 s / 15 s), bad status, parse error | error.jsp | step 1 via "Back to search" | user-profile-app/src/com/acme/profile/integration/MiddlewareClient.java:60-104, user-profile-app/WebContent/WEB-INF/struts-config.xml:12-16, user-profile-app/WebContent/jsp/error.jsp:6-9 |
| 3 | System error | Mobile null or < 4 chars | 500 → error.jsp | error page | user-profile-app/WebContent/jsp/profile/results.jsp:23 (Inferred) |

## J2 · View a customer's profile

| # | User action | Application component | API | Data exchanged | Logic performed | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 1 | Opens a profile | `ProfileAction#view` → `view.jsp` | `GET /profile.do?method=view&userId=<id>`; outbound POST `mw.endpoint.get` on cache miss | in: `userId`; out: name, userId, msisdn, email, nric, DOB dd/MM/yyyy + age, segment, status, badge | App-wide cache, no expiry (`BE`); NRIC masked unless PROFILE_ADMIN (`SEC`); audit VIEW (`DATA`); age from yyyyMMdd, -1 if missing (`BE`); VIP if PLATINUM/GOLD else Senior if age ≥ 65 (`FE`); name unescaped (`FE`) | user-profile-app/WebContent/WEB-INF/struts-config.xml:39-46, user-profile-app/src/com/acme/profile/web/ProfileAction.java:24-46, user-profile-app/src/com/acme/profile/service/ProfileService.java:22-23, user-profile-app/src/com/acme/profile/service/ProfileService.java:50-101, user-profile-app/src/com/acme/profile/integration/MiddlewareClient.java:46-52, user-profile-app/WebContent/jsp/profile/view.jsp:5-37 | Confirmed |

Exits

| From step | Exit | Trigger | User sees | Goes to | Evidence |
|---|---|---|---|---|---|
| 1 | Not found | MW returns no profile | "No profile found for user <id>." | search.jsp | user-profile-app/src/com/acme/profile/web/ProfileAction.java:31-37, user-profile-app/src/ApplicationResources.properties:18 |
| 1 | System error | MiddlewareException | error.jsp | J1 step 1 | user-profile-app/src/ApplicationResources.properties:19 |
| 1 | System error | DOB not yyyyMMdd (page re-parses) | 500 → error.jsp | error page | user-profile-app/WebContent/jsp/profile/view.jsp:14-18 (Inferred) |
| 1 | Missing DOB | DOB null | Date of birth shows " (-1)" | stays | user-profile-app/WebContent/jsp/profile/view.jsp:35, user-profile-app/src/com/acme/profile/service/ProfileService.java:86-89 |

## J3 · Refresh a profile

| # | User action | Application component | API | Data exchanged | Logic performed | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 1 | Clicks "Refresh from source" | `view.jsp` button (location.href), `ProfileAction#refresh` | `GET /profile.do?method=refresh&userId=<id>` → 302 view | in: `userId` | Evicts shared cache entry for all staff (`BE`); no audit for refresh (`DATA`); state change on GET (`BE`) | user-profile-app/WebContent/jsp/profile/view.jsp:40-41, user-profile-app/src/com/acme/profile/web/ProfileAction.java:49-57, user-profile-app/src/com/acme/profile/service/ProfileService.java:67-71 | Confirmed |
| 2 | Sees refreshed profile | `ProfileAction#view` → `view.jsp` | as J2 step 1 (cache miss) | as J2 | as J2, new VIEW audit row | user-profile-app/src/com/acme/profile/web/ProfileAction.java:24-46 | Confirmed |

## J4 · Get into the app

| # | User action | Application component | API | Data exchanged | Logic performed | Evidence | Status |
|---|---|---|---|---|---|---|---|
| 1 | Requests any screen | `EncodingFilter` (/*), `AuthFilter` (*.do) | any `*.do` | in: session `staffUser` (staffId, roles) | No staffUser → redirect /login.jsp (`SEC`); no role → 403 (`SEC`); session timeout 20 min (`SEC`) | user-profile-app/WebContent/WEB-INF/web.xml:14-33, user-profile-app/WebContent/WEB-INF/web.xml:50-52, user-profile-app/src/com/acme/profile/web/AuthFilter.java:22-37 | Confirmed |
| 2 | Signs in | Not in this codebase | /login.jsp (absent) | out: `staffUser` in session | Unknown | user-profile-app/src/com/acme/profile/web/AuthFilter.java:30, user-profile-app/WebContent/WEB-INF/struts-config.xml:19 | Open (Q-01) |

## Orphans

| Item | Kind | Note | Evidence | Status |
|---|---|---|---|---|
| /login.jsp | Screen | Redirect target; file not in repo | user-profile-app/src/com/acme/profile/web/AuthFilter.java:30 | Confirmed |
| Global forwards `login`, `search` | Routes | Declared, never used by a handler | user-profile-app/WebContent/WEB-INF/struts-config.xml:18-21 | Confirmed |
| /profile.do without method | Endpoint | DispatchAction with no `unspecified()` → 500 | user-profile-app/src/com/acme/profile/web/ProfileAction.java:19-58 | Inferred |
| /jsp/**/*.jsp direct URLs | Screens | Not under WEB-INF, not covered by AuthFilter → 500 | user-profile-app/WebContent/WEB-INF/web.xml:30-33 | Inferred |

## Open questions (technical detail)

| ID | Question | Evidence | Maps to "Things to confirm" # |
|---|---|---|---|
| Q-01 | What sets `staffUser` (with roles) and serves /login.jsp? | user-profile-app/src/com/acme/profile/web/AuthFilter.java:28-31 | 1 |
| Q-02 | Email search audits target "": blank mobile trims to "" not null, so `msisdn != null ? msisdn : email` picks "". | user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:33, user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:38 | 2 |
| Q-03 | Truncated banner uses `>=`, so it shows at exactly 20. | user-profile-app/src/com/acme/profile/web/ProfileSearchAction.java:55, user-profile-app/src/com/acme/profile/service/ProfileService.java:43-45 | 3 |
| Q-04 | Static cache, no expiry. | user-profile-app/src/com/acme/profile/service/ProfileService.java:22-23 | 4 |
| Q-05 | Masking differs per screen/role; email never masked. | user-profile-app/WebContent/jsp/profile/results.jsp:23, user-profile-app/src/com/acme/profile/web/ProfileAction.java:39-41 | 5 |
| Q-06 | Does error.jsp render the exception message? | user-profile-app/WebContent/jsp/error.jsp:8 | 6 |
