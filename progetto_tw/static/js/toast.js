function showBootstrapAlertWithIcon(text, type) {
    let alertClass = 'alert-success';
    let iconClass = 'bi-check-circle-fill';
    let heading = 'Successo!';

    switch(type) {
        case 'bad':
            alertClass = 'alert-danger';
            iconClass = 'bi-exclamation-triangle-fill';
            heading = 'Errore!';
            break;
        case 'warning':
            alertClass = 'alert-warning';
            iconClass = 'bi-exclamation-circle-fill';
            heading = 'Attenzione!';
            break;
        case 'good':
        default:
            alertClass = 'alert-success';
            iconClass = 'bi-check-circle-fill';
            heading = 'Successo!';
            break;
    }

    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show fixed-top mx-auto mt-3 d-flex align-items-center"
             style="max-width: 60%; z-index: 2000;" role="alert">
            <i class="bi ${iconClass} mr-2" style="font-size: 1.5rem;"></i>
            <div>
                <strong>${heading}</strong> ${text}
            </div>
            <button type="button" class="close ml-auto align-self-center" data-dismiss="alert" aria-label="Close" style="margin-top: 3px;">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    `;

    $('body').append(alertHtml);

    const alertElement = $('.alert.fixed-top').last();
    const timeout = setTimeout(() => {
        alertElement.alert('close');
    }, 4000);

    alertElement.on('closed.bs.alert', function () {
        clearTimeout(timeout);
    });
}
