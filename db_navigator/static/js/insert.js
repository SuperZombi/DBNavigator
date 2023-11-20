function submitInsert(event){
	var xhr = new XMLHttpRequest();
	xhr.open("POST", window.location.href); 
	xhr.onload = function(){
		if (xhr.status != 200){
			alert(`[${xhr.status}] ${xhr.statusText}`)
		} else{
			let result = JSON.parse(xhr.response)
			if (!result.successfully){
				document.querySelector("#sql-error").innerText = result.sql_error
				document.querySelector("#sql-error").scrollIntoView()
			} else{
				window.location.href = "content"
			}
		}
	};
	var formData = new FormData(event.target); 
	xhr.send(formData);
}
