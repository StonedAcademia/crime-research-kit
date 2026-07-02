# app

The app layer is the use-case boundary. It chooses the runner, creates tool
adapters, and returns serializable workflow state to callers. It should not
contain lane heuristics, CRK command details, or LangGraph node definitions.
