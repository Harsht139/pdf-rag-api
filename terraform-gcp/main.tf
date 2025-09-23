resource "google_service_account" "service_account" {
  project      = var.project_id
  account_id   = var.service_account_name
  display_name = var.service_account_name
}

resource "google_service_account_iam_member" "impersonation_binding" {
  count                  = var.impersonation_user_email != "" ? 1 : 0
  service_account_id     = google_service_account.service_account.name
  role                   = "roles/iam.serviceAccountTokenCreator"
  member                 = "user:${var.impersonation_user_email}"
}
