Feature: Stages

    @auth
    Scenario: Add stage
        Given empty "stages"

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user",
        "task_status": "todo"
        }
        """

        Then we get new resource
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user",
        "task_status": "todo"
        }
        """


    @auth
    Scenario: Add stage - no name
        Given empty "stages"

        When we post to "/stages"
        """
        {
        "description": "Show content items created by the current logged user"
        }
        """

        Then we get error 400
        """
        {"_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"}, "_issues": {"name": {"required": 1}}, "_status": "ERR"}
        """


    @auth
    Scenario: Add stage - no description
        Given empty "stages"
        When we post to "/stages"
        """
        {
        "name": "show my content"
        }
        """

        Then we get new resource
        """
        {
        "name": "show my content"
        }
        """

    @auth
    Scenario: Add stage - with desk
        Given empty "stages"

        When we post to "desks"
        """
        {"name": "Sports Desk"}
        """

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "desk": "#DESKS_ID#",
        "description": "Show content items created by the current logged user"
        }
        """

        Then we get new resource
        """
        {
        "name": "show my content",
        "desk": "#DESKS_ID#",
        "description": "Show content items created by the current logged user"
        }
        """

    @auth
    Scenario: Edit stage - modify description and name
        Given empty "stages"

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user"
        }
        """

        Then we get new resource
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user"
        }
        """
        When we patch latest
        """
        {
        "description": "Show content that I just updated",
        "name": "My stage"
        }
        """
        Then we get updated response

    @auth
    Scenario: Get tasks for stage
        Given empty "desks"
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        When we post to "/stages"
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user"
        }
        """
        When we post to "desks"
        """
        {"name": "Sports Desk", "incoming_stage": "#STAGES_ID#"}
        """
        When we post to "tasks"
	    """
        [{"slugline": "first task", "type": "text", "task": {"desk":"#DESKS_ID#", "stage" :"#STAGES_ID#"}}]
	    """
        When we post to "archive"
        """
        [{"type": "text"}]
        """
        And we get "/tasks"
        Then we get list with 1 items
	    """
        {"_items": [{"slugline": "first task", "type": "text", "task": {"desk": "#DESKS_ID#", "stage": "#STAGES_ID#"}}]}
	    """

        When we get "/tasks?where={"task.stage": "#STAGES_ID#"}"
        Then we get list with 1 items
	    """
        {"_items": [{"slugline": "first task", "type": "text", "task": {"desk": "#DESKS_ID#", "stage": "#STAGES_ID#"}}]}
	    """

        @auth
    Scenario: Can delete empty stage
        Given empty "desks"
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        When we post to "/stages"
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user"
        }
        """
        When we post to "desks"
        """
        {"name": "Sports Desk", "incoming_stage": "#STAGES_ID#"}
        """
        When we post to "tasks"
	    """
        [{"slugline": "first task", "type": "text", "task": {"desk":"#DESKS_ID#", "stage" :"0"}}]
	    """
        When we post to "archive"
        """
        [{"type": "text"}]
        """
        When we delete "/stages/#STAGES_ID#"
        Then we get response code 200

    @auth
    Scenario: Cannot delete stage if there are documents
        Given empty "desks"
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        When we post to "/stages"
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user"
        }
        """
        When we post to "desks"
        """
        {"name": "Sports Desk", "incoming_stage": "#STAGES_ID#"}
        """
        When we post to "tasks"
	    """
        [{"slugline": "first task", "type": "text", "task": {"desk":"#DESKS_ID#", "stage" :"#STAGES_ID#"}}]
	    """
        When we post to "archive"
        """
        [{"type": "text"}]
        """
        And we get "/tasks"
        Then we get list with 1 items
	    """
        {"_items": [{"slugline": "first task", "type": "text", "task": {"desk": "#DESKS_ID#", "stage": "#STAGES_ID#"}}]}
	    """

        When we delete "/stages/#STAGES_ID#"

        Then we get response code 403
