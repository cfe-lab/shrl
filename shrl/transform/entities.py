from shared_schema.data import schema_data

Person = schema_data.namedtuple_for("Person")
Case = schema_data.namedtuple_for("Case")
BehaviorData = schema_data.namedtuple_for("BehaviorData")
TreatmentData = schema_data.namedtuple_for("TreatmentData")
LossToFollowUp = schema_data.namedtuple_for("LossToFollowUp")
ClinicalData = schema_data.namedtuple_for("ClinicalData")
Isolate = schema_data.namedtuple_for("Isolate")
ClinicalIsolate = schema_data.namedtuple_for("ClinicalIsolate")
Sequence = schema_data.namedtuple_for("Sequence")
Alignment = schema_data.namedtuple_for("Alignment")
Substitution = schema_data.namedtuple_for("Substitution")
