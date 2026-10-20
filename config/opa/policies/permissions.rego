# Minimale Werkzeug-Richtlinie für den F13-Chat (f13-demo, selbst geschrieben).
#
# Chat v3 fragt OPA, welche Werkzeuge (Tools) eine Person im agentischen Chat
# benutzen darf, und startet ohne erreichbares OPA gar nicht.
#
# ANNAHME (ungeprüft): Paketname und Eingabeformat. Erwartet wird z. B.
#   {
#     "tools": ["werkzeug_a", "werkzeug_b"],
#     "user":  {"authenticated": false, "roles": []}
#   }
# Im Zweifel mit `docker compose logs opa` nachsehen: Die Decision-Logs zeigen die
# tatsächliche Eingabe (decision_logs.console=true).
package f13.tools.permissions

# Werkzeug -> Menge der Rollen, von denen mindestens eine nötig ist.
# In der Demo hat kein Werkzeug eine Rollenpflicht, also ist alles erlaubt.
# Beispiel: required_roles := {"websuche": {"f13-recherche"}}
required_roles := {}

default allow := false

# Erlaubt, wenn das Werkzeug keine Rolle verlangt ...
tool_allowed(tool) if {
	not required_roles[tool]
}

# ... oder die Person angemeldet ist und eine der verlangten Rollen hat.
tool_allowed(tool) if {
	input.user.authenticated == true
	some role in required_roles[tool]
	role in input.user.roles
}

allowed_tools contains tool if {
	some tool in input.tools
	tool_allowed(tool)
}

denied_tools contains tool if {
	some tool in input.tools
	not tool_allowed(tool)
}

allow if {
	count(denied_tools) == 0
}
