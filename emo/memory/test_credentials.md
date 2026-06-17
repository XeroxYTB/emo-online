# Test Credentials for Émo

## Comptes admin lifetime (zéro paywall)
- `hugo@example.com` / `emo-test-2026`
- `huglostalatac@gmail.com` / `emo2026`

## Comptes standards (10 messages/jour gratuits)
- Tout signup avec un autre email → quota daily

## Daily quota reset
- À minuit UTC chaque jour
- Le compteur `daily_count` est remis à 0 si `daily_day != today`

## Notes
- Cookie session_token (httpOnly, secure, samesite=none)
- Bearer token accepté aussi
- Stripe sk_test_emergent pour le checkout €20 lifetime
