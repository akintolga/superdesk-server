Feature: Stages

    @auth
    Scenario: Add stage and verify order
        Given empty "stages"
        Given "desks"
        """
        [{"name": "test_desk"}]
        """

        When we get "/stages/#desks.incoming_stage#"
        Then we get existing resource
        """
        {
        "name": "New",
        "task_status": "todo",
        "desk": "#desks._id#",
        "desk_order": 1
        }
        """

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user",
        "task_status": "in-progress",
        "desk": "#desks._id#"
        }
        """

        Then we get new resource
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user",
        "task_status": "in-progress",
        "desk": "#desks._id#",
        "desk_order": 2
        }
        """


    @auth
    Scenario: Add stage - no name
        Given empty "stages"
        Given "desks"
        """
        [{"name": "test_desk"}]
        """

        When we post to "/stages"
        """
        {
        "description": "Show content items created by the current logged user"
        }
        """

        Then we get error 400
        """
        {
        "_error": {"code": 400, "message": "Insertion failure: 1 document(s) contain(s) error(s)"},
        "_issues": {"name": {"required": 1}, "task_status": {"required": 1}, "desk": {"required": 1}}, "_status": "ERR"
        }
        """


    @auth
    Scenario: Add stage - no description
        Given empty "stages"
        Given "desks"
        """
        [{"name": "test_desk"}]
        """

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "task_status": "todo",
        "desk": "#desks._id#"
        }
        """

        Then we get new resource
        """
        {
        "name": "show my content",
        "task_status": "todo",
        "desk": "#desks._id#",
        "desk_order": 2
        }
        """


    @auth
    Scenario: Edit stage - modify description and name
        Given empty "stages"
        Given "desks"
        """
        [{"name": "test_desk"}]
        """

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user",
        "task_status": "todo",
        "desk": "#desks._id#"
        }
        """

        Then we get new resource
        """
        {
        "name": "show my content",
        "description": "Show content items created by the current logged user",
        "task_status": "todo",
        "desk": "#desks._id#"
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
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """

        When we post to "tasks"
	    """
        [{"slugline": "first task", "type": "text", "task": {"desk":"#desks._id#", "stage" :"#desks.incoming_stage#"}}]
	    """
        When we post to "archive"
        """
        [{"type": "text"}]
        """
        And we get "/tasks"

        Then we get list with 1 items
	    """
        {"_items": [{"slugline": "first task", "type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]}
	    """

        When we get "/tasks?where={"task.stage": "#desks.incoming_stage#"}"

        Then we get list with 1 items
	    """
        {"_items": [{"slugline": "first task", "type": "text", "task": {"desk": "#desks._id#", "stage": "#desks.incoming_stage#"}}]}
	    """


    @auth
    Scenario: Can delete empty stage
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "task_status": "todo",
        "desk": "#desks._id#"
        }
        """

        When we post to "tasks"
	    """
        [{"slugline": "first task", "type": "text", "task": {"desk":"#desks._id#", "stage" :"#desks.incoming_stage#"}}]
	    """
	    Then we get new resource
        When we post to "archive"
        """
        [{"type": "text"}]
        """
        When we delete "/stages/#stages._id#"
        Then we get response code 204


    @auth
    Scenario: Cannot delete stage if there are documents
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """

        When we post to "/stages"
        """
        {
        "name": "show my content",
        "task_status": "todo",
        "desk": "#desks._id#"
        }
        """

        When we patch "/stages/#stages._id#"
        """
        {"desk":"#desks._id#"}
        """
        When we post to "tasks"
	    """
        [{"slugline": "first task", "type": "text", "task": {"desk":"#desks._id#", "stage" :"#stages._id#"}}]
	    """
	    Then we get new resource
        When we post to "archive"
        """
        [{"type": "text"}]
        """
        When we delete "/stages/#stages._id#"

        Then we get response code 403


    @auth
    Scenario: Get invisible stages
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """

        When we post to "/stages"
        """
        {
        "name": "invisible1",
        "task_status": "todo",
        "desk": "#desks._id#",
        "is_visible" : false
        }
        """

        When we post to "/stages"
        """
        {
        "name": "invisible2",
        "task_status": "todo",
        "desk": "#desks._id#",
        "is_visible" : false
        }
        """


        Then we get two invisible stages


    @auth
    Scenario: Get visible stages
        Given empty "archive"
        Given empty "tasks"
        Given empty "stages"
        Given "desks"
        """
        [{"name": "Sports Desk"}]
        """

        When we post to "/stages"
        """
        {
        "name": "invisible1",
        "task_status": "todo",
        "desk": "#desks._id#",
        "is_visible" : false
        }
        """

        When we post to "/stages"
        """
        {
        "name": "invisible2",
        "task_status": "todo",
        "desk": "#desks._id#",
        "is_visible" : true
        }
        """


        Then we get two visible stages