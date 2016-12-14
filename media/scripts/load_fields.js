
    var respondToSelect = true;

    $(document).ready(function () {

        // Function code here.
        $('select').on("change", function (event) {
            var el = $(event.target)

            // the element id that maps to a metadata object
            var selected_id = el.prop('id')

            // id and selected key value of each form element
            var frm = $("form").serializeFormJSON();
            frm['selected_id'] = selected_id;

            thingy = JSON.stringify(frm);

            // populate session data before showing the status page
            $.post("/selectChanged/", thingy,
                function (data) {
                    updateFields(data);
                })
            .fail(function (xhr, textStatus, errorThrown) {
                errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
                window.open(errtext, '_self');
            });
        });

    });

    function initializeFields() {

        // populate session data before showing the status page
        $.post("/initializeFields/", "{}",
            function (data) {
                updateFields(data);
            })
        .fail(function (xhr, textStatus, errorThrown) {
            errtext = 'data:text/html;base64,' + window.btoa(xhr.responseText);
            window.open(errtext, '_self');
        });
    }

    function updateFields(list)
    {
        for (var i = 0; i < list.length; i++) {
            var item = list[i];
            var id = item.meta_id;
            var data = item.selection_list;

            updateField(id, data);
        }
    }

    function updateField(fieldID, data) {

        var select = "#" + fieldID;
        $(select).empty();
        $(select).val('')

        var s2 = $(select).data('select2');
        if (s2) {
            $(select).select2('data', null);
            $(select).select2({
                allowClear: true,
                data: data
            });
        }
        else {
            $(select).text(data[0].text)
        }
    }
