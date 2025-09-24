resource "google_service_account" "service_account" {
  project      = var.project_id
  account_id   = var.service_account_name
  display_name = var.service_account_name
}

# Allow a specific user to impersonate the service account
resource "google_service_account_iam_member" "impersonation_binding" {
  count              = var.impersonation_user_email != "" ? 1 : 0
  service_account_id = google_service_account.service_account.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "user:${var.impersonation_user_email}"
}

# Grant project-level roles to the service account
resource "google_project_iam_member" "service_account_roles" {
  for_each = toset([
    "roles/artifactregistry.admin",
    "roles/iam.serviceAccountUser",
    "roles/run.admin",
    "roles/cloudtasks.admin"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.service_account.email}"
}
